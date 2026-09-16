from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore


result_store = InMemoryAnalysisResultStore()
app = create_app(result_store)
