# water_quality_vertex_ai.py
import os
import io
import json
import pickle
import base64
import argparse
import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime
from flask import Flask, request, jsonify
from google.cloud import storage
from google.cloud import firestore
from google.cloud import pubsub_v1
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from concurrent.futures import ThreadPoolExecutor

# Configuration
MAX_CONCURRENT_REQUESTS = 20
PREDICTION_TIMEOUT = 5  # seconds
MODEL_BUCKET = os.environ.get('MODEL_BUCKET', 'your-model-bucket')
DATA_BUCKET = os.environ.get('DATA_BUCKET', 'your-data-bucket')
PROJECT_ID = os.environ.get('PROJECT_ID', 'your-project-id')

# Initialize Flask app
app = Flask(__name__)

# Initialize GCP clients
storage_client = storage.Client()
db = firestore.Client()
publisher = pubsub_vublisher = pubsub_v1.PublisherClient()

# Thread pool for concurrent predictions
prediction_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS)

class WaterPotabilityNN(tf.keras.Model):
    """Neural Network model for water potability prediction"""
    def __init__(self):
        super(WaterPotabilityNN, self).__init__()
        self.dense1 = tf.keras.layers.Dense(64, activation='relu')
        self.dropout = tf.keras.layers.Dropout(0.3)
        self.dense2 = tf.keras.layers.Dense(32, activation='relu')
        self.output_layer = tf.keras.layers.Dense(2, activation=None)
        
    def call(self, inputs, training=False):
        x = self.dense1(inputs)
        x = self.dropout(x, training=training)
        x = self.dense2(x)
        return self.output_layer(x)

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Download a file from Google Cloud Storage"""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """Upload a file to Google Cloud Storage"""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

def load_data_from_gcs(bucket_name, file_name):
    """Load CSV data from GCS"""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    content = blob.download_as_string()
    return pd.read_csv(io.StringIO(content.decode('utf-8')))

def train_model(data_path, output_dir):
    """Train the water quality model"""
    # Load and prepare data
    data = load_data_from_gcs(data_path['bucket'], data_path['file'])
    data = data.dropna()
    
    X = data.drop('Potability', axis=1).values
    y = data['Potability'].values
    
    # Normalize features
    scaler = StandardScaler()
    X = scaler.fit_transform(X).astype(np.float32)
    y = y.astype(np.int32)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.25, random_state=42, stratify=y_train)
    
    # Create and train model
    model = WaterPotabilityNN()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(0.001),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=['accuracy']
    )
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=32
    )
    
    # Evaluate
    test_loss, test_acc = model.evaluate(X_test, y_test)
    print(f"Test Accuracy: {test_acc*100:.2f}%")
    
    # Save artifacts
    model.save('model.h5')
    with open('scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    
    # Upload to GCS
    upload_to_gcs(output_dir['bucket'], 'model.h5', f"{output_dir['prefix']}/model.h5")
    upload_to_gcs(output_dir['bucket'], 'scaler.pkl', f"{output_dir['prefix']}/scaler.pkl")

def load_model():
    """Load model and scaler from GCS"""
    model_path = os.environ.get('MODEL_PATH', 'water_quality/model.h5')
    scaler_path = os.environ.get('SCALER_PATH', 'water_quality/scaler.pkl')
    
    download_from_gcs(MODEL_BUCKET, model_path, '/tmp/model.h5')
    download_from_gcs(MODEL_BUCKET, scaler_path, '/tmp/scaler.pkl')
    
    model = tf.keras.models.load_model('/tmp/model.h5')
    with open('/tmp/scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    
    return model, scaler

def publish_prediction(device_id, prediction):
    """Publish prediction to Pub/Sub"""
    topic_path = publisher.topic_path(
        PROJECT_ID,
        os.environ.get('PREDICTION_TOPIC', 'water_quality_predictions')
    )
    
    data = json.dumps({
        'device_id': device_id,
        'prediction': prediction,
        'timestamp': datetime.now().isoformat()
    }).encode('utf-8')
    
    future = publisher.publish(topic_path, data)
    future.result()

def process_prediction(data):
    """Process a single prediction request"""
    try:
        device_id = data.get('device_id', 'unknown')
        
        # Validate input
        required_fields = ['ph', 'Hardness', 'Solids', 'Chloramines', 
                          'Sulfate', 'Conductivity', 'Organic_carbon', 
                          'Trihalomethanes', 'Turbidity']
        
        for field in required_fields:
            if field not in data:
                return {'error': f'Missing field: {field}'}, 400
        
        # Load model if not loaded
        if not hasattr(app, 'model') or not hasattr(app, 'scaler'):
            app.model, app.scaler = load_model()
        
        # Prepare features
        features = np.array([
            data['ph'], data['Hardness'], data['Solids'],
            data['Chloramines'], data['Sulfate'], data['Conductivity'],
            data['Organic_carbon'], data['Trihalomethanes'], data['Turbidity']
        ]).reshape(1, -1).astype(np.float32)
        
        # Scale and predict
        features_scaled = app.scaler.transform(features)
        logits = app.model.predict(features_scaled)
        probabilities = tf.nn.softmax(logits)[0]
        prediction = int(np.argmax(logits, axis=1)[0])
        
        # Prepare response
        response = {
            'device_id': device_id,
            'prediction': prediction,
            'prediction_label': 'Potable' if prediction == 1 else 'Not Potable',
            'confidence': float(probabilities[prediction]),
            'prob_potable': float(probabilities[1]),
            'status': 'success'
        }
        
        # Publish to Pub/Sub
        publish_prediction(device_id, response)
        
        # Update device stats in Firestore
        device_ref = db.collection('devices').document(device_id)
        device_ref.set({
            'last_seen': datetime.now().isoformat(),
            'total_readings': firestore.Increment(1)
        }, merge=True)
        
        # Store reading
        reading_ref = db.collection('readings').document()
        reading_ref.set({
            'device_id': device_id,
            'timestamp': datetime.now().isoformat(),
            **response
        })
        
        return response, 200
    
    except Exception as e:
        return {'error': str(e), 'status': 'error'}, 500

@app.before_first_request
def initialize():
    """Load model on startup"""
    app.model, app.scaler = load_model()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

@app.route('/predict', methods=['POST'])
def predict():
    """Endpoint for prediction requests"""
    data = request.get_json()
    
    # Submit to thread pool
    future = prediction_executor.submit(process_prediction, data)
    
    try:
        result, status_code = future.result(timeout=PREDICTION_TIMEOUT)
        return jsonify(result), status_code
    except concurrent.futures.TimeoutError:
        return jsonify({'error': 'Prediction timeout', 'status': 'error'}), 504
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/devices', methods=['GET'])
def list_devices():
    """List all registered devices"""
    devices_ref = db.collection('devices')
    docs = devices_ref.stream()
    
    devices = []
    for doc in docs:
        devices.append(doc.to_dict())
    
    return jsonify(devices)

@app.route('/device/<device_id>', methods=['GET'])
def get_device(device_id):
    """Get device details and recent readings"""
    device_ref = db.collection('devices').document(device_id)
    device = device_ref.get()
    
    if not device.exists:
        return jsonify({'error': 'Device not found'}), 404
    
    # Get recent readings
    readings_ref = db.collection('readings')
    query = readings_ref.where('device_id', '==', device_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10)
    readings = [doc.to_dict() for doc in query.stream()]
    
    return jsonify({
        'device': device.to_dict(),
        'recent_readings': readings
    })

def register_device(device_id, firmware_version=None, location=None):
    """Register a new device"""
    device_ref = db.collection('devices').document(device_id)
    device_ref.set({
        'device_id': device_id,
        'firmware_version': firmware_version,
        'location': location,
        'first_seen': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'status': 'active',
        'total_readings': 0
    }, merge=True)
    
    # Publish registration event
    topic_path = publisher.topic_path(
        PROJECT_ID,
        os.environ.get('DEVICE_TOPIC', 'device_events')
    )
    publisher.publish(topic_path, json.dumps({
        'type': 'device_registered',
        'device_id': device_id,
        'timestamp': datetime.now().isoformat()
    }).encode('utf-8'))

@app.route('/register', methods=['POST'])
def register():
    """Endpoint for device registration"""
    data = request.get_json()
    device_id = data.get('device_id')
    
    if not device_id:
        return jsonify({'error': 'device_id is required'}), 400
    
    register_device(
        device_id,
        data.get('firmware_version'),
        data.get('location')
    )
    
    return jsonify({'status': 'success', 'device_id': device_id})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    
    # Train command
    train_parser = subparsers.add_parser('train')
    train_parser.add_argument('--data-bucket', default=DATA_BUCKET)
    train_parser.add_argument('--data-file', required=True)
    train_parser.add_argument('--output-bucket', default=MODEL_BUCKET)
    train_parser.add_argument('--output-prefix', default='water_quality')
    
    # Serve command
    serve_parser = subparsers.add_parser('serve')
    serve_parser.add_argument('--port', type=int, default=8080)
    
    args = parser.parse_args()
    
    if args.command == 'train':
        train_model(
            data_path={'bucket': args.data_bucket, 'file': args.data_file},
            output_dir={'bucket': args.output_bucket, 'prefix': args.output_prefix}
        )
    elif args.command == 'serve':
        app.run(host='0.0.0.0', port=args.port)
    else:
        parser.print_help()