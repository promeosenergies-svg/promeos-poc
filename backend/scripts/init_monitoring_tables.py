"""Create monitoring tables in promeos.db."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from models.energy_models import MonitoringSnapshot, MonitoringAlert

MonitoringSnapshot.__table__.create(bind=engine, checkfirst=True)
MonitoringAlert.__table__.create(bind=engine, checkfirst=True)
print("Monitoring tables created (monitoring_snapshot, monitoring_alert)")
