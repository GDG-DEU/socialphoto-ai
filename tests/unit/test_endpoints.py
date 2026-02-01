"""Unit tests for API endpoints using pytest and TestClient."""
import pytest


class TestAnalyzeEndpoint:
    """Tests for POST /analyze endpoint."""
    
    def test_analyze_creates_job(self, client):
        """Should create a job and return 202 with job_id."""
        response = client.post("/analyze", json={
            "post_id": "test_post_123",
            "image_url": "https://example.com/test-image.jpg"
        })
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
    
    def test_analyze_invalid_url(self, client):
        """Should reject invalid image URLs."""
        response = client.post("/analyze", json={
            "post_id": "test_post_123",
            "image_url": "not-a-valid-url"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_missing_post_id(self, client):
        """Should reject request without post_id."""
        response = client.post("/analyze", json={
            "image_url": "https://example.com/test-image.jpg"
        })
        
        assert response.status_code == 422


class TestAnalyzeJobStatus:
    """Tests for GET /analyze/{job_id} endpoint."""
    
    def test_get_completed_job(self, client_with_job):
        """Should return completed job with results."""
        response = client_with_job.get("/analyze/test-job-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["aesthetic_score"] == 0.85
        assert "sunset" in data["result"]["suggested_tags"]
    
    def test_get_nonexistent_job(self, client):
        """Should return 404 for non-existent job."""
        response = client.get("/analyze/fake-job-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSimSearchEndpoint:
    """Tests for POST /sim-search endpoint."""
    
    def test_search_with_text(self, client):
        """Should return results for text query."""
        response = client.post("/sim-search", json={
            "query_text": "beautiful sunset",
            "top_k": 3
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) <= 3
    
    def test_search_with_image(self, client):
        """Should return results for image URL query."""
        response = client.post("/sim-search", json={
            "image_url": "https://example.com/query.jpg",
            "top_k": 2
        })
        
        assert response.status_code == 200
        assert "results" in response.json()
    
    def test_search_with_both(self, client):
        """Should return results for combined text and image query."""
        response = client.post("/sim-search", json={
            "query_text": "mountain landscape",
            "image_url": "https://example.com/mountain.jpg",
            "top_k": 5
        })
        
        assert response.status_code == 200
    
    def test_search_requires_query(self, client):
        """Should reject request without text or image."""
        response = client.post("/sim-search", json={
            "top_k": 3
        })
        
        assert response.status_code == 400
        assert "at least one" in response.json()["detail"].lower()


class TestChatEndpoint:
    """Tests for POST /chat endpoint."""
    
    def test_basic_chat(self, client):
        """Should return a reply for basic message."""
        response = client.post("/chat", json={
            "user_id": "user_123",
            "message": "Hello, how are you?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert len(data["reply"]) > 0
    
    def test_chat_search_keyword_triggers_action(self, client):
        """Should trigger search_images action when 'search' is mentioned."""
        response = client.post("/chat", json={
            "user_id": "user_123",
            "message": "Can you search for sunset images?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] is not None
        assert any(a["type"] == "search_images" for a in data["actions"])
    
    def test_chat_analyze_keyword_triggers_action(self, client):
        """Should trigger analyze_photo action when 'analyze' is mentioned."""
        response = client.post("/chat", json={
            "user_id": "user_456",
            "message": "Please analyze this photo"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] is not None
        assert any(a["type"] == "analyze_photo" for a in data["actions"])
    
    def test_chat_with_history(self, client):
        """Should accept conversation history."""
        response = client.post("/chat", json={
            "user_id": "user_789",
            "message": "What did I ask before?",
            "history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        })
        
        assert response.status_code == 200
    
    def test_chat_no_action_for_regular_message(self, client):
        """Should not trigger actions for regular messages."""
        response = client.post("/chat", json={
            "user_id": "user_123",
            "message": "Hello, how are you?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] is None


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""
    
    def test_health_returns_status(self, client):
        """Should return health status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["online", "degraded", "offline"]
        assert "models_loaded" in data
    
    def test_health_includes_redis(self, client):
        """Should include Redis in healthy components."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "redis" in data["models_loaded"]
