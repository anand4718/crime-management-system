import pandas as pd
from datetime import datetime, timedelta
from app.models import Complaint, Alert
from app import db

def detect_crime_trends():
    """Analyzes complaint data to find recent spikes in crime categories."""
    print(f"[{datetime.now()}] AI Trend Detector: Starting analysis...")
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    complaints = Complaint.query.filter(Complaint.timestamp >= seven_days_ago).all()

    if len(complaints) < 5:  # Don't run on very small datasets
        print("AI Trend Detector: Not enough recent complaints to analyze.")
        return

    data = [{
        'date': c.timestamp.date(),
        'category': c.category,
        'location': c.location.lower().strip() if c.location else 'unknown'
    } for c in complaints]
    df = pd.DataFrame(data)

    if df.empty:
        print("AI Trend Detector: DataFrame is empty, skipping analysis.")
        return

    daily_counts = df.groupby(['date', 'location', 'category']).size().reset_index(name='count')
    significant_spikes = daily_counts[daily_counts['count'] > 2] # Rule: more than 2 of the same crime in a day/location

    for index, row in significant_spikes.iterrows():
        alert_title = f"Spike in {row['category']}"
        alert_date = row['date']
        
        # Check if an alert for this trend on this day already exists
        existing_alert = Alert.query.filter(Alert.title == alert_title, db.func.date(Alert.timestamp) == alert_date).first()
        
        if not existing_alert:
            alert = Alert(
                title=alert_title,
                description=f"Detected {row['count']} reports of '{row['category']}' in {row['location'].title()} on {alert_date.strftime('%Y-%m-%d')}."
            )
            db.session.add(alert)
            print(f"AI Trend Detector: New trend found - {alert.description}")

    db.session.commit()
    print(f"[{datetime.now()}] AI Trend Detector: Analysis complete.")