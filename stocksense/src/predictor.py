"""
StockSense Predictor
Makes predictions using trained model for real-time inventory monitoring
"""

import pandas as pd
import numpy as np
import joblib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockSensePredictor:
    """
    Real-time predictor for stockout risk assessment
    """
    
    def __init__(self, model_path: str = '../models/stockout_model.pkl'):
        """
        Initialize predictor with trained model
        
        Args:
            model_path (str): Path to trained model file
        """
        self.model_path = model_path
        self.model_data = None
        self.load_model()
        
    def load_model(self):
        """Load the trained model and associated components"""
        try:
            self.model_data = joblib.load(self.model_path)
            logger.info(f"Model loaded successfully from {self.model_path}")
        except FileNotFoundError:
            logger.error(f"Model file not found: {self.model_path}")
            logger.error("Please train the model first by running model.py")
            raise
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def prepare_prediction_data(self, inventory_data: pd.DataFrame, 
                               sales_history: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Prepare data for prediction by engineering features
        
        Args:
            inventory_data (DataFrame): Current inventory levels
            sales_history (DataFrame, optional): Historical sales data
            
        Returns:
            DataFrame: Prepared data for prediction
        """
        df = inventory_data.copy()
        
        # If sales history is provided, aggregate it
        if sales_history is not None:
            sales_agg = sales_history.groupby('product_id').agg({
                'daily_demand': ['mean', 'std', 'max'],
                'stockout': 'sum'
            }).reset_index()
            
            # Flatten column names
            sales_agg.columns = [
                'product_id', 'avg_daily_demand', 'demand_std', 
                'max_daily_demand', 'total_stockouts'
            ]
            
            df = df.merge(sales_agg, on='product_id', how='left')
        
        # Fill missing values with defaults if sales history not available
        if 'avg_daily_demand' not in df.columns:
            df['avg_daily_demand'] = 10.0  # Default demand
        if 'demand_std' not in df.columns:
            df['demand_std'] = 2.0  # Default variability
        if 'max_daily_demand' not in df.columns:
            df['max_daily_demand'] = df['avg_daily_demand'] * 2
        if 'total_stockouts' not in df.columns:
            df['total_stockouts'] = 0
            
        # Engineer features similar to training
        df['demand_variability'] = df['demand_std'] / df['avg_daily_demand']
        df['stock_coverage_days'] = df['current_stock'] / df['avg_daily_demand']
        df['stockout_rate'] = df['total_stockouts'] / 365
        
        # Add default values for missing features
        required_features = [
            'price', 'category', 'subcategory', 'seasonal_factor',
            'weekend_sales_ratio', 'holiday_sales_ratio'
        ]
        
        for feature in required_features:
            if feature not in df.columns:
                if feature == 'price':
                    df[feature] = 50.0  # Default price
                elif feature in ['category', 'subcategory']:
                    df[feature] = 'General'  # Default category
                elif feature == 'seasonal_factor':
                    df[feature] = 1.0  # No seasonality
                else:
                    df[feature] = 0.5  # Default ratio
        
        return df
    
    def predict_single_product(self, product_data: Dict) -> Dict:
        """
        Predict stockout risk for a single product
        
        Args:
            product_data (dict): Product information
            
        Returns:
            dict: Prediction results with risk score and recommendations
        """
        # Convert to DataFrame
        df = pd.DataFrame([product_data])
        
        # Prepare data
        df_prepared = self.prepare_prediction_data(df)
        
        # Make prediction using the loaded model components
        try:
            # Use the StockSenseModel's prediction logic
            from model import StockSenseModel
            
            # Create temporary model instance and load components
            temp_model = StockSenseModel()
            temp_model.model = self.model_data['model']
            temp_model.scaler = self.model_data.get('scaler')
            temp_model.encoders = self.model_data['encoders']
            temp_model.feature_names = self.model_data['feature_names']
            temp_model.is_trained = True
            
            # Make prediction
            predictions, probabilities = temp_model.predict(df_prepared)
            
            risk_score = probabilities[0]
            is_high_risk = predictions[0]
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            # Fallback simple prediction
            stock_days = product_data.get('current_stock', 0) / max(product_data.get('avg_daily_demand', 1), 1)
            lead_time = product_data.get('supplier_lead_time', 7)
            
            risk_score = max(0, min(1, 1 - (stock_days / (lead_time * 2))))
            is_high_risk = 1 if risk_score > 0.5 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(product_data, risk_score)
        
        return {
            'product_id': product_data.get('product_id', 'Unknown'),
            'risk_score': float(risk_score),
            'risk_level': 'High' if is_high_risk else 'Low',
            'risk_category': self._categorize_risk(risk_score),
            'recommendations': recommendations,
            'prediction_timestamp': datetime.now().isoformat()
        }
    
    def predict_batch(self, inventory_data: pd.DataFrame, 
                      sales_history: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Predict stockout risk for multiple products
        
        Args:
            inventory_data (DataFrame): Current inventory levels for multiple products
            sales_history (DataFrame, optional): Historical sales data
            
        Returns:
            DataFrame: Prediction results for all products
        """
        logger.info(f"Making batch predictions for {len(inventory_data)} products")
        
        # Prepare data
        df_prepared = self.prepare_prediction_data(inventory_data, sales_history)
        
        try:
            # Use the loaded model for prediction
            from model import StockSenseModel
            
            temp_model = StockSenseModel()
            temp_model.model = self.model_data['model']
            temp_model.scaler = self.model_data.get('scaler')
            temp_model.encoders = self.model_data['encoders']
            temp_model.feature_names = self.model_data['feature_names']
            temp_model.is_trained = True
            
            predictions, probabilities = temp_model.predict(df_prepared)
            
        except Exception as e:
            logger.error(f"Error in batch prediction: {e}")
            # Fallback predictions
            predictions = []
            probabilities = []
            
            for _, row in df_prepared.iterrows():
                stock_days = row.get('current_stock', 0) / max(row.get('avg_daily_demand', 1), 1)
                lead_time = row.get('supplier_lead_time', 7)
                
                risk_score = max(0, min(1, 1 - (stock_days / (lead_time * 2))))
                probabilities.append(risk_score)
                predictions.append(1 if risk_score > 0.5 else 0)
        
        # Add predictions to results
        results = inventory_data.copy()
        results['risk_score'] = probabilities
        results['risk_prediction'] = predictions
        results['risk_level'] = ['High' if p == 1 else 'Low' for p in predictions]
        results['risk_category'] = [self._categorize_risk(score) for score in probabilities]
        results['prediction_timestamp'] = datetime.now().isoformat()
        
        # Sort by risk score (highest risk first)
        results = results.sort_values('risk_score', ascending=False)
        
        logger.info(f"Batch prediction completed. High risk products: {sum(predictions)}")
        
        return results\n    \n    def get_high_risk_products(self, inventory_data: pd.DataFrame, \n                              threshold: float = 0.5) -> pd.DataFrame:\n        \"\"\"\n        Get products with high stockout risk\n        \n        Args:\n            inventory_data (DataFrame): Current inventory data\n            threshold (float): Risk threshold for high risk classification\n            \n        Returns:\n            DataFrame: High risk products sorted by risk score\n        \"\"\"\n        predictions = self.predict_batch(inventory_data)\n        high_risk = predictions[predictions['risk_score'] >= threshold]\n        \n        return high_risk.sort_values('risk_score', ascending=False)\n    \n    def _categorize_risk(self, risk_score: float) -> str:\n        \"\"\"\n        Categorize risk score into risk levels\n        \n        Args:\n            risk_score (float): Risk probability score\n            \n        Returns:\n            str: Risk category\n        \"\"\"\n        if risk_score < 0.3:\n            return 'Low Risk'\n        elif risk_score < 0.7:\n            return 'Medium Risk'\n        else:\n            return 'High Risk'\n    \n    def _generate_recommendations(self, product_data: Dict, risk_score: float) -> List[str]:\n        \"\"\"\n        Generate actionable recommendations based on risk assessment\n        \n        Args:\n            product_data (dict): Product information\n            risk_score (float): Calculated risk score\n            \n        Returns:\n            list: List of recommendations\n        \"\"\"\n        recommendations = []\n        \n        current_stock = product_data.get('current_stock', 0)\n        avg_demand = product_data.get('avg_daily_demand', 1)\n        lead_time = product_data.get('supplier_lead_time', 7)\n        min_stock = product_data.get('minimum_stock_level', 10)\n        \n        stock_days = current_stock / max(avg_demand, 1)\n        \n        if risk_score > 0.7:\n            recommendations.append(\"🚨 URGENT: Place emergency order immediately\")\n            recommendations.append(f\"📦 Current stock will last only {stock_days:.1f} days\")\n            \n        elif risk_score > 0.5:\n            recommendations.append(\"⚠️  Schedule reorder within 24 hours\")\n            recommendations.append(f\"📊 Stock coverage: {stock_days:.1f} days\")\n        \n        if current_stock < min_stock:\n            recommendations.append(f\"📉 Below minimum stock level ({min_stock} units)\")\n        \n        if stock_days < lead_time:\n            recommendations.append(f\"⏰ Stock will run out before next delivery ({lead_time} days)\")\n        \n        # Positive recommendations for low risk\n        if risk_score < 0.3:\n            recommendations.append(\"✅ Inventory levels are healthy\")\n            recommendations.append(f\"📈 Current stock covers {stock_days:.1f} days of demand\")\n        \n        # Calculate optimal reorder quantity\n        safety_stock = avg_demand * lead_time * 1.5  # 150% of lead time demand\n        reorder_qty = max(0, safety_stock - current_stock)\n        \n        if reorder_qty > 0:\n            recommendations.append(f\"📋 Suggested reorder quantity: {int(reorder_qty)} units\")\n        \n        return recommendations\n    \n    def generate_dashboard_data(self, inventory_data: pd.DataFrame) -> Dict:\n        \"\"\"\n        Generate comprehensive dashboard data for inventory monitoring\n        \n        Args:\n            inventory_data (DataFrame): Current inventory data\n            \n        Returns:\n            dict: Dashboard data with metrics and insights\n        \"\"\"\n        predictions = self.predict_batch(inventory_data)\n        \n        # Calculate key metrics\n        total_products = len(predictions)\n        high_risk_count = sum(predictions['risk_prediction'])\n        medium_risk_count = sum(predictions['risk_score'].between(0.3, 0.7))\n        low_risk_count = total_products - high_risk_count - medium_risk_count\n        \n        # Risk distribution\n        risk_distribution = {\n            'High Risk': high_risk_count,\n            'Medium Risk': medium_risk_count,\n            'Low Risk': low_risk_count\n        }\n        \n        # Top risk products\n        top_risk_products = predictions.head(10)[[\n            'product_id', 'current_stock', 'avg_daily_demand', \n            'risk_score', 'risk_category'\n        ]].to_dict('records')\n        \n        # Category analysis\n        if 'category' in predictions.columns:\n            category_risk = predictions.groupby('category').agg({\n                'risk_score': 'mean',\n                'risk_prediction': 'sum'\n            }).round(3).to_dict()\n        else:\n            category_risk = {}\n        \n        return {\n            'timestamp': datetime.now().isoformat(),\n            'summary': {\n                'total_products': total_products,\n                'high_risk_products': high_risk_count,\n                'risk_percentage': round(high_risk_count / total_products * 100, 1)\n            },\n            'risk_distribution': risk_distribution,\n            'top_risk_products': top_risk_products,\n            'category_analysis': category_risk,\n            'alerts': self._generate_alerts(predictions)\n        }\n    \n    def _generate_alerts(self, predictions: pd.DataFrame) -> List[Dict]:\n        \"\"\"\n        Generate alerts for immediate attention\n        \n        Args:\n            predictions (DataFrame): Prediction results\n            \n        Returns:\n            list: List of alert dictionaries\n        \"\"\"\n        alerts = []\n        \n        # Critical stock alerts\n        critical_products = predictions[predictions['risk_score'] > 0.8]\n        for _, product in critical_products.iterrows():\n            alerts.append({\n                'type': 'critical',\n                'product_id': product.get('product_id', 'Unknown'),\n                'message': f\"Critical stockout risk: {product['risk_score']:.1%}\",\n                'priority': 'high'\n            })\n        \n        # Low stock alerts\n        if 'current_stock' in predictions.columns and 'minimum_stock_level' in predictions.columns:\n            low_stock = predictions[predictions['current_stock'] < predictions['minimum_stock_level']]\n            for _, product in low_stock.iterrows():\n                alerts.append({\n                    'type': 'low_stock',\n                    'product_id': product.get('product_id', 'Unknown'),\n                    'message': f\"Below minimum stock level\",\n                    'priority': 'medium'\n                })\n        \n        return alerts[:10]  # Limit to top 10 alerts\n\ndef main():\n    \"\"\"\n    Main function for testing the predictor\n    \"\"\"\n    try:\n        # Initialize predictor\n        predictor = StockSensePredictor()\n        \n        # Load sample data\n        inventory_data = pd.read_csv('../data/sample_inventory.csv')\n        \n        logger.info(\"Testing StockSense Predictor...\")\n        \n        # Test single product prediction\n        sample_product = {\n            'product_id': 'TEST001',\n            'current_stock': 15,\n            'avg_daily_demand': 5,\n            'supplier_lead_time': 7,\n            'minimum_stock_level': 20,\n            'price': 25.99,\n            'category': 'Electronics'\n        }\n        \n        single_result = predictor.predict_single_product(sample_product)\n        print(\"\\n📊 Single Product Prediction:\")\n        print(json.dumps(single_result, indent=2))\n        \n        # Test batch prediction\n        if len(inventory_data) > 0:\n            batch_results = predictor.predict_batch(inventory_data.head(5))\n            print(f\"\\n📈 Batch Prediction Results ({len(batch_results)} products):\")\n            print(batch_results[['product_id', 'current_stock', 'risk_score', 'risk_level']].to_string(index=False))\n            \n            # Generate dashboard data\n            dashboard = predictor.generate_dashboard_data(inventory_data.head(10))\n            print(\"\\n📊 Dashboard Summary:\")\n            print(f\"   Total Products: {dashboard['summary']['total_products']}\")\n            print(f\"   High Risk: {dashboard['summary']['high_risk_products']}\")\n            print(f\"   Risk Percentage: {dashboard['summary']['risk_percentage']}%\")\n        \n        logger.info(\"✅ Predictor testing completed successfully!\")\n        \n    except Exception as e:\n        logger.error(f\"Error testing predictor: {e}\")\n        logger.info(\"Make sure to train the model first by running: python model.py\")\n\nif __name__ == \"__main__\":\n    main()"