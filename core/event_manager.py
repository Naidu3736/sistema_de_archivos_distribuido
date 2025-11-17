from datetime import datetime

class EventManager:
    def __init__(self):
        self.subscribers = []
    
    def subscribe(self, callback):
        """Suscribirse a eventos"""
        self.subscribers.append(callback)
    
    def publish(self, event_type, data):
        """Publicar evento"""
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        for callback in self.subscribers:
            callback(event)


event_manager = EventManager()