from google.cloud import firestore
from google.cloud import pubsub_v1
import json

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

def register_device(request):
    request_json = request.get_json()
    device_id = request_json.get('device_id')
    
    if not device_id:
        return {'error': 'device_id is required'}, 400
    
    doc_ref = db.collection('devices').document(device_id)
    doc_ref.set({
        'device_id': device_id,
        'first_seen': firestore.SERVER_TIMESTAMP,
        'last_seen': firestore.SERVER_TIMESTAMP,
        'status': 'active'
    }, merge=True)
    
    topic_path = publisher.topic_path(os.environ['PROJECT_ID'], 'device_events')
    publisher.publish(topic_path, json.dumps({
        'type': 'device_registered',
        'device_id': device_id
    }).encode('utf-8'))
    
    return {'status': 'success', 'device_id': device_id}