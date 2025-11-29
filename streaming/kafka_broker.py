"""
Lightweight Kafka-like Message Broker
Simulates Kafka topics and pub-sub for demonstration
"""
import json
import time
from collections import defaultdict
from datetime import datetime
from threading import Lock, Thread
import queue

class KafkaBroker:
    """In-memory Kafka-like broker for local development"""
    
    def __init__(self):
        self.topics = defaultdict(lambda: queue.Queue(maxsize=1000))
        self.subscribers = defaultdict(list)
        self.lock = Lock()
        self.running = True
        
    def create_topic(self, topic_name):
        """Create a new topic"""
        with self.lock:
            if topic_name not in self.topics:
                self.topics[topic_name] = queue.Queue(maxsize=1000)
                self.subscribers[topic_name] = []
                print(f"[OK] Topic created: {topic_name}")
                
    def publish(self, topic_name, message):
        """Publish message to topic"""
        with self.lock:
            if topic_name not in self.topics:
                self.create_topic(topic_name)
            
            # Add timestamp
            if isinstance(message, dict):
                message['kafka_timestamp'] = datetime.now().isoformat()
            
            try:
                self.topics[topic_name].put(message, timeout=1)
                return True
            except queue.Full:
                print(f"⚠️ Topic {topic_name} is full, dropping message")
                return False
                
    def subscribe(self, topic_name, callback):
        """Subscribe to topic with callback function"""
        with self.lock:
            if topic_name not in self.topics:
                self.create_topic(topic_name)
            self.subscribers[topic_name].append(callback)
            
    def consume(self, topic_name, timeout=1):
        """Consume single message from topic"""
        try:
            return self.topics[topic_name].get(timeout=timeout)
        except queue.Empty:
            return None
            
    def start_consumer_thread(self, topic_name, callback):
        """Start background thread to consume messages"""
        def consumer_loop():
            while self.running:
                message = self.consume(topic_name, timeout=0.1)
                if message:
                    try:
                        callback(message)
                    except Exception as e:
                        print(f"❌ Error in consumer callback: {e}")
                        
        thread = Thread(target=consumer_loop, daemon=True)
        thread.start()
        return thread
        
    def get_stats(self):
        """Get broker statistics"""
        stats = {}
        with self.lock:
            for topic_name, topic_queue in self.topics.items():
                stats[topic_name] = {
                    'messages_pending': topic_queue.qsize(),
                    'subscribers': len(self.subscribers[topic_name])
                }
        return stats
        
    def stop(self):
        """Stop the broker"""
        self.running = False


# Global broker instance
_broker = None

def get_broker():
    """Get or create global broker instance"""
    global _broker
    if _broker is None:
        _broker = KafkaBroker()
    return _broker


if __name__ == "__main__":
    # Test the broker
    broker = get_broker()
    
    # Create topic
    broker.create_topic("sensor_data")
    
    # Publish test messages
    for i in range(5):
        message = {
            "sensor_id": f"SENSOR_{i}",
            "temperature": 25.0 + i,
            "timestamp": datetime.now().isoformat()
        }
        broker.publish("sensor_data", message)
        print(f"📤 Published: {message}")
        
    # Consume messages
    print("\n📥 Consuming messages:")
    for i in range(5):
        msg = broker.consume("sensor_data")
        if msg:
            print(f"  Received: {msg}")
            
    print(f"\n📊 Stats: {broker.get_stats()}")
