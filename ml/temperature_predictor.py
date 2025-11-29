"""
Temperature Prediction Model using Prophet
==========================================
Predicts next day's temperature for each city using Facebook Prophet

Project: DEPI Final Project - IoT Data Pipeline with ML
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("⚠️ Prophet not installed. Install with: pip install prophet")

# Database path
DB_PATH = Path(__file__).parent.parent / "database" / "iot_warehouse.db"

class TemperaturePredictor:
    """Temperature prediction model using Prophet"""
    
    def __init__(self, db_path=None):
        """Initialize predictor"""
        self.db_path = db_path or DB_PATH
        self.models = {}  # Store trained models per city
        self.predictions = {}
        
    def get_training_data(self, city_name, days=30):
        """
        Get historical temperature data for a city
        
        Args:
            city_name: Name of the city
            days: Number of days of history to use (default 30)
        
        Returns:
            DataFrame with 'ds' (datetime) and 'y' (temperature) columns
        """
        conn = sqlite3.connect(str(self.db_path))
        
        query = f"""
        SELECT 
            t.ts as ds,
            f.temperature as y
        FROM fact_weather_reading f
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_location l ON f.location_id = l.location_id
        WHERE l.city_name = '{city_name}'
            AND t.ts >= datetime('now', '-{days} days')
        ORDER BY t.ts
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print(f"⚠️ No data found for {city_name}")
            return None
        
        df['ds'] = pd.to_datetime(df['ds'])
        print(f"✓ Loaded {len(df)} data points for {city_name}")
        
        return df
    
    def train_model(self, city_name, training_days=30):
        """
        Train Prophet model for a specific city
        
        Args:
            city_name: Name of the city
            training_days: Days of historical data to use
        
        Returns:
            Trained Prophet model or None if failed
        """
        if not PROPHET_AVAILABLE:
            print("❌ Prophet not available. Cannot train model.")
            return None
        
        # Get training data
        df = self.get_training_data(city_name, training_days)
        
        if df is None or len(df) < 2:
            print(f"❌ Insufficient data for {city_name} (need at least 2 points)")
            return None
        
        # Create and train Prophet model
        print(f"🔄 Training model for {city_name}...")
        
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,  # Not enough data for yearly patterns
            changepoint_prior_scale=0.05,  # More flexible to changes
            seasonality_mode='additive'
        )
        
        try:
            model.fit(df)
            self.models[city_name] = model
            print(f"✅ Model trained successfully for {city_name}")
            return model
        except Exception as e:
            print(f"❌ Error training model for {city_name}: {e}")
            return None
    
    def predict_next_day(self, city_name, periods=24):
        """
        Predict temperature for the next day (hourly)
        
        Args:
            city_name: Name of the city
            periods: Number of hours to predict (default 24)
        
        Returns:
            DataFrame with predictions
        """
        # Train model if not already trained
        if city_name not in self.models:
            model = self.train_model(city_name)
            if model is None:
                return None
        else:
            model = self.models[city_name]
        
        # Create future dataframe for next 24 hours
        future = model.make_future_dataframe(periods=periods, freq='H')
        
        # Make predictions
        forecast = model.predict(future)
        
        # Get only future predictions (not historical)
        last_date = model.history['ds'].max()
        predictions = forecast[forecast['ds'] > last_date].copy()
        
        # Clean up predictions
        predictions['city_name'] = city_name
        predictions['predicted_temp'] = predictions['yhat'].round(2)
        predictions['lower_bound'] = predictions['yhat_lower'].round(2)
        predictions['upper_bound'] = predictions['yhat_upper'].round(2)
        
        self.predictions[city_name] = predictions
        
        print(f"✅ Generated {len(predictions)} predictions for {city_name}")
        print(f"   Average predicted temp: {predictions['predicted_temp'].mean():.1f}°C")
        
        return predictions[['ds', 'city_name', 'predicted_temp', 'lower_bound', 'upper_bound']]
    
    def predict_all_cities(self):
        """
        Predict temperature for all cities in database
        
        Returns:
            Combined DataFrame with all predictions
        """
        # Get list of cities
        conn = sqlite3.connect(str(self.db_path))
        cities_df = pd.read_sql_query("SELECT DISTINCT city_name FROM dim_location", conn)
        conn.close()
        
        cities = cities_df['city_name'].tolist()
        print(f"\n{'='*60}")
        print(f"🔮 TEMPERATURE PREDICTION FOR {len(cities)} CITIES")
        print(f"{'='*60}\n")
        
        all_predictions = []
        
        for city in cities:
            print(f"\n📍 Processing {city}...")
            predictions = self.predict_next_day(city)
            
            if predictions is not None:
                all_predictions.append(predictions)
        
        if not all_predictions:
            print("\n❌ No predictions generated")
            return None
        
        # Combine all predictions
        combined = pd.concat(all_predictions, ignore_index=True)
        
        print(f"\n{'='*60}")
        print(f"✅ PREDICTIONS COMPLETE")
        print(f"{'='*60}")
        print(f"Total predictions: {len(combined)}")
        print(f"Cities: {len(cities)}")
        print(f"Time range: {combined['ds'].min()} to {combined['ds'].max()}")
        
        return combined
    
    def save_predictions_to_db(self, predictions_df):
        """
        Save predictions to a new table in the database
        
        Args:
            predictions_df: DataFrame with predictions
        """
        if predictions_df is None or predictions_df.empty:
            print("❌ No predictions to save")
            return
        
        conn = sqlite3.connect(str(self.db_path))
        
        # Create predictions table if it doesn't exist
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_temperature_predictions (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_timestamp DATETIME NOT NULL,
            city_name TEXT NOT NULL,
            predicted_temp REAL NOT NULL,
            lower_bound REAL NOT NULL,
            upper_bound REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            model_version TEXT DEFAULT 'prophet_v1'
        )
        """)
        
        # Save predictions
        predictions_df['created_at'] = datetime.now()
        predictions_df['model_version'] = 'prophet_v1'
        predictions_df.rename(columns={'ds': 'prediction_timestamp'}, inplace=True)
        
        predictions_df.to_sql(
            'ml_temperature_predictions',
            conn,
            if_exists='append',
            index=False
        )
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Saved {len(predictions_df)} predictions to database")
    
    def get_latest_predictions(self, city_name=None):
        """
        Get latest predictions from database
        
        Args:
            city_name: Filter by city name (optional)
        
        Returns:
            DataFrame with latest predictions
        """
        conn = sqlite3.connect(str(self.db_path))
        
        if city_name:
            query = f"""
            SELECT * FROM ml_temperature_predictions
            WHERE city_name = '{city_name}'
            ORDER BY prediction_timestamp
            """
        else:
            query = """
            SELECT * FROM ml_temperature_predictions
            WHERE created_at = (SELECT MAX(created_at) FROM ml_temperature_predictions)
            ORDER BY city_name, prediction_timestamp
            """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_prediction_accuracy(self, city_name, hours_back=24):
        """
        Calculate prediction accuracy by comparing past predictions with actual values
        
        Args:
            city_name: Name of the city
            hours_back: How many hours back to check
        
        Returns:
            Dictionary with accuracy metrics
        """
        conn = sqlite3.connect(str(self.db_path))
        
        # Get predictions from the past
        query = f"""
        SELECT 
            p.prediction_timestamp,
            p.predicted_temp,
            AVG(f.temperature) as actual_temp
        FROM ml_temperature_predictions p
        JOIN dim_location l ON p.city_name = l.city_name
        JOIN fact_weather_reading f ON f.location_id = l.location_id
        JOIN dim_time t ON f.time_id = t.time_id
        WHERE p.city_name = '{city_name}'
            AND ABS((julianday(t.ts) - julianday(p.prediction_timestamp)) * 24) < 1
            AND p.prediction_timestamp < datetime('now')
            AND p.prediction_timestamp >= datetime('now', '-{hours_back} hours')
        GROUP BY p.prediction_timestamp, p.predicted_temp
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        # Calculate metrics
        df['error'] = df['actual_temp'] - df['predicted_temp']
        df['abs_error'] = abs(df['error'])
        
        metrics = {
            'city': city_name,
            'predictions_checked': len(df),
            'mae': df['abs_error'].mean(),
            'rmse': np.sqrt((df['error'] ** 2).mean()),
            'mean_error': df['error'].mean(),
            'accuracy_percent': 100 * (1 - df['abs_error'].mean() / df['actual_temp'].mean())
        }
        
        return metrics


def main():
    """Main function to run predictions"""
    print("\n" + "="*60)
    print("🌡️ TEMPERATURE PREDICTION SYSTEM")
    print("="*60 + "\n")
    
    # Check if Prophet is available
    if not PROPHET_AVAILABLE:
        print("❌ Prophet is not installed!")
        print("📦 Install with: pip install prophet")
        print("   or: pip install pystan prophet")
        return
    
    # Create predictor
    predictor = TemperaturePredictor()
    
    # Generate predictions for all cities
    predictions = predictor.predict_all_cities()
    
    if predictions is not None:
        # Save to database
        predictor.save_predictions_to_db(predictions)
        
        # Show summary
        print(f"\n📊 PREDICTION SUMMARY")
        print(f"{'='*60}")
        for city in predictions['city_name'].unique():
            city_preds = predictions[predictions['city_name'] == city]
            avg_temp = city_preds['predicted_temp'].mean()
            min_temp = city_preds['predicted_temp'].min()
            max_temp = city_preds['predicted_temp'].max()
            print(f"{city:15} | Avg: {avg_temp:5.1f}°C | Range: {min_temp:.1f}°C - {max_temp:.1f}°C")
    
    print("\n✅ Prediction process complete!")


if __name__ == "__main__":
    main()
