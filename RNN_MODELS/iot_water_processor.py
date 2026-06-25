from google.cloud import firestore
import json
import base64

db = firestore.Client()

def process_prediction(event, context):
    pubsub_message = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    
    device_id = pubsub_message.get('device_id')
    prediction = pubsub_message.get('prediction')
    
    if not device_id or not prediction:
        print("Invalid message format")
        return
    
    # Update device stats
    device_ref = db.collection('devices').document(device_id)
    device_ref.update({
        'last_seen': firestore.SERVER_TIMESTAMP,
        'total_readings': firestore.Increment(1)
    })
    
    # Store reading
    readings_ref = db.collection('readings').document()
    readings_ref.set({
        'device_id': device_id,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'prediction': prediction['prediction'],
        'confidence': prediction['confidence'],
        'prob_potable': prediction['prob_potable']
    })