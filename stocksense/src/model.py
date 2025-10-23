"""
StockSense Machine Learning Model
Predicts stockout risk for inventory management
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import xgboost as xgb
import joblib
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockSenseModel:
    """
    Machine Learning model for predicting stockout risk
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.encoders = {}
        self.feature_names = []
        self.is_trained = False
        
    def engineer_features(self, data):
        """
        Create meaningful features for prediction
        
        Args:
            data (DataFrame): Raw inventory data
            
        Returns:
            DataFrame: Engineered features
        """
        df_features = data.copy()
        
        # Handle missing values
        df_features['demand_variability'] = df_features['demand_variability'].fillna(0)
        
        # Price categories
        df_features['price_category'] = pd.cut(df_features['price'], 
                                              bins=[0, 20, 100, 500, float('inf')],
                                              labels=['Low', 'Medium', 'High', 'Premium'])
        
        # Demand categories
        df_features['demand_category'] = pd.cut(df_features['avg_daily_demand'],
                                               bins=[0, 10, 50, 100, float('inf')],
                                               labels=['Low', 'Medium', 'High', 'Very High'])
        
        # Risk indicators
        df_features['stockout_rate'] = df_features['total_stockouts'] / 365
        df_features['is_fast_moving'] = (df_features['avg_daily_demand'] > df_features['avg_daily_demand'].median()).astype(int)
        df_features['lead_time_risk'] = (df_features['supplier_lead_time'] > 7).astype(int)
        
        # Seasonal indicators
        df_features['is_seasonal'] = (df_features['seasonal_factor'] > 1.5).astype(int)
        
        # Stock health metrics
        df_features['stock_health_score'] = (
            df_features['stock_coverage_days'] / df_features['supplier_lead_time']
        )
        
        return df_features
    
    def prepare_features(self, data, fit_encoders=True):
        """
        Prepare features for modeling
        
        Args:
            data (DataFrame): Feature engineered data
            fit_encoders (bool): Whether to fit new encoders or use existing ones
            
        Returns:
            tuple: (X, feature_names)
        """
        df_model = data.copy()
        
        # Encode categorical variables
        categorical_cols = ['category', 'subcategory', 'price_category', 'demand_category']
        
        for col in categorical_cols:
            if fit_encoders:
                if col not in self.encoders:
                    self.encoders[col] = LabelEncoder()
                df_model[f'{col}_encoded'] = self.encoders[col].fit_transform(df_model[col])
            else:
                if col in self.encoders:
                    # Handle unseen categories
                    df_model[f'{col}_encoded'] = df_model[col].map(
                        dict(zip(self.encoders[col].classes_, 
                                self.encoders[col].transform(self.encoders[col].classes_)))
                    ).fillna(-1)  # Assign -1 to unseen categories
        
        # Select features for modeling
        feature_cols = [
            'price', 'supplier_lead_time', 'minimum_stock_level', 'seasonal_factor',
            'avg_daily_demand', 'demand_std', 'max_daily_demand', 'total_stockouts',
            'weekend_sales_ratio', 'holiday_sales_ratio', 'current_stock',
            'days_since_restock', 'demand_variability', 'stock_coverage_days',
            'category_encoded', 'subcategory_encoded', 'price_category_encoded',
            'demand_category_encoded', 'stockout_rate', 'is_fast_moving',
            'lead_time_risk', 'is_seasonal', 'stock_health_score'
        ]
        
        # Only use columns that exist in the data
        available_cols = [col for col in feature_cols if col in df_model.columns]
        X = df_model[available_cols]
        
        if fit_encoders:
            self.feature_names = available_cols
            
        return X, available_cols
    
    def train(self, data, target_column='is_high_risk', model_type='random_forest'):
        """
        Train the stockout prediction model
        
        Args:
            data (DataFrame): Training data
            target_column (str): Name of target column
            model_type (str): Type of model to train ('random_forest', 'xgboost', 'logistic')
        """
        logger.info("Starting model training...")
        
        # Feature engineering
        data_engineered = self.engineer_features(data)
        
        # Prepare features
        X, feature_names = self.prepare_features(data_engineered, fit_encoders=True)
        y = data_engineered[target_column]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model based on type
        if model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
            self.model.fit(X_train, y_train)
            
        elif model_type == 'xgboost':
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            self.model.fit(X_train, y_train)
            
        elif model_type == 'logistic':
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            self.model = LogisticRegression(random_state=42)
            self.model.fit(X_train_scaled, y_train)
            
            # Use scaled data for evaluation
            X_test = X_test_scaled
        
        # Evaluate model
        if self.scaler:
            y_pred = self.model.predict(X_test)
            y_prob = self.model.predict_proba(X_test)[:, 1]
        else:
            y_pred = self.model.predict(X_test)
            y_prob = self.model.predict_proba(X_test)[:, 1]
        
        # Calculate performance metrics
        auc_score = roc_auc_score(y_test, y_prob)
        accuracy = (y_pred == y_test).mean()
        
        logger.info(f"Model training completed!")
        logger.info(f"AUC Score: {auc_score:.4f}")
        logger.info(f"Accuracy: {accuracy:.4f}")
        
        # Print classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Low Risk', 'High Risk']))
        
        self.is_trained = True
        
        return {
            'auc_score': auc_score,
            'accuracy': accuracy,
            'model_type': model_type
        }
    
    def predict(self, data):
        """
        Make predictions on new data
        
        Args:
            data (DataFrame): Data to make predictions on
            
        Returns:
            tuple: (predictions, probabilities)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Feature engineering
        data_engineered = self.engineer_features(data)
        
        # Prepare features
        X, _ = self.prepare_features(data_engineered, fit_encoders=False)
        
        # Scale if necessary
        if self.scaler:
            X = self.scaler.transform(X)
        
        # Make predictions
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)[:, 1]
        
        return predictions, probabilities
    
    def get_feature_importance(self):
        """
        Get feature importance from trained model
        
        Returns:
            DataFrame: Feature importance scores
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")
        
        if hasattr(self.model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return importance_df
        else:
            logger.warning("Model does not have feature importance attribute")
            return None
    
    def save_model(self, filepath):
        """
        Save trained model to file
        
        Args:
            filepath (str): Path to save model
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'encoders': self.encoders,
            'feature_names': self.feature_names,
            'timestamp': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath):
        """
        Load trained model from file
        
        Args:
            filepath (str): Path to load model from
        """
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.scaler = model_data.get('scaler')
        self.encoders = model_data['encoders']
        self.feature_names = model_data['feature_names']
        self.is_trained = True
        
        logger.info(f"Model loaded from {filepath}")

def main():
    """
    Main function to train and save the model
    """
    # Load training data
    try:
        data = pd.read_csv('../data/ml_training_data.csv')
        logger.info(f"Loaded training data: {data.shape}")
    except FileNotFoundError:
        logger.error("Training data not found. Please run data_generation.py first.")
        return
    
    # Initialize and train model
    stocksense = StockSenseModel()
    
    # Train different models and compare
    models = ['random_forest', 'xgboost', 'logistic']
    results = {}
    
    for model_type in models:
        logger.info(f"\nTraining {model_type} model...")
        stocksense_temp = StockSenseModel()
        result = stocksense_temp.train(data, model_type=model_type)
        results[model_type] = result
        
        # Save the best model so far
        if not results or result['auc_score'] > max(r['auc_score'] for r in results.values() if r != result):
            stocksense = stocksense_temp
            best_model_type = model_type
    
    logger.info(f"\nBest model: {best_model_type} with AUC: {results[best_model_type]['auc_score']:.4f}")
    
    # Save the best model
    import os
    os.makedirs('../models', exist_ok=True)
    stocksense.save_model('../models/stockout_model.pkl')
    
    # Show feature importance
    importance_df = stocksense.get_feature_importance()
    if importance_df is not None:
        print("\nTop 10 Feature Importances:")
        print(importance_df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()