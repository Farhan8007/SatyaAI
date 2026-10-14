"""
MongoDB connection using Motor (async driver).
Collections are exposed as simple properties for use across routers/services.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


class Database:
    client: AsyncIOMotorClient | None = None

    def connect(self):
        # Default pymongo server-selection timeout is 30s -- if MongoDB is
        # down, every request would hang for 30 seconds before failing,
        # which feels like the whole app is frozen. 5s is still generous
        # for a real connection but fails fast and clearly when it's not
        # running at all.
        self.client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)

    def close(self):
        if self.client:
            self.client.close()

    @property
    def db(self):
        return self.client[settings.mongo_db_name]

    # Collections -----------------------------------------------------
    @property
    def users(self):
        return self.db["users"]

    @property
    def papers(self):
        return self.db["papers"]

    @property
    def audit_logs(self):
        return self.db["audit_logs"]

    @property
    def alerts(self):
        return self.db["alerts"]

    @property
    def approvals(self):
        return self.db["approvals"]

    @property
    def reports(self):
        return self.db["reports"]


database = Database()
