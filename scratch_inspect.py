from app.db.session import get_db_session
from app.db.models import RecoveryOpportunity, RecoveryAction, ActionStatus

with get_db_session() as session:
    q = session.query(RecoveryOpportunity).join(RecoveryAction).filter(RecoveryAction.status == ActionStatus.pending.value)
    print("SQL:", str(q))
    res = q.all()
    print(f"Results count: {len(res)}")

