"""Unit tests for API endpoints using pytest and TestClient."""
import pytest
from unittest.mock import MagicMock, patch


class TestAnalyzeEndpoint:
    """Tests for POST /analyze endpoint."""
    
    def test_analyze_creates_job(self, client):
        """Should create a job and return 202 with job_id."""
        response = client.post("/analyze", json={
            "post_id": "test_post_123",
            "cloudinary_public_id": "samples/test-image"
        })
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
    
    def test_analyze_invalid_cloudinary_id(self, client):
        """Should reject request with empty cloudinary_public_id."""
        response = client.post("/analyze", json={
            "post_id": "test_post_123",
            "cloudinary_public_id": ""
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_missing_post_id(self, client):
        """Should reject request without post_id."""
        response = client.post("/analyze", json={
            "cloudinary_public_id": "samples/test-image"
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
        """Should return results for image query."""
        response = client.post("/sim-search", json={
            "cloudinary_public_id": "samples/query",
            "top_k": 2
        })
        
        assert response.status_code == 200
        assert "results" in response.json()
    
    def test_search_with_both(self, client):
        """Should return results for combined text and image query."""
        response = client.post("/sim-search", json={
            "query_text": "mountain landscape",
            "cloudinary_public_id": "samples/mountain",
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


class TestPineconeEndpoints:
    """Tests for Pinecone endpoints /upsert and /delete-record."""
    
    def test_upsert_endpoint_success(self, client):
        """Should upsert vectors and return success."""
        
        with patch("app.pinecone_service") as mock_pinecone_service:
            # Setup mock
            mock_pinecone_service.upsert_vectors.return_value = True
            
            payload = {
                "items": [
                    {
                        "post_id": "p123",
                        "cloudinary_public_id": "img/photo1"
                    },
                    {
                        "post_id": "p124",
                        "cloudinary_public_id": "img/photo2"
                    }
                ]
            }
            
            response = client.post("/upsert", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["count"] == 2
            
            mock_pinecone_service.upsert_vectors.assert_called_once()
            call_kwargs = mock_pinecone_service.upsert_vectors.call_args.kwargs
            assert len(call_kwargs["vectors"]) == 2
            # vector id is cloudinary_public_id
            assert call_kwargs["vectors"][0]["id"] == "img/photo1"
            assert call_kwargs["vectors"][1]["id"] == "img/photo2"

    def test_upsert_endpoint_failure(self, client):
        """Should return 500 on upsert failure."""
        
        with patch("app.pinecone_service") as mock_pinecone_service:
            mock_pinecone_service.upsert_vectors.return_value = False
            
            payload = {
                "items": [
                    {
                        "post_id": "p123",
                        "cloudinary_public_id": "img/photo1"
                    }
                ]
            }
            
            response = client.post("/upsert", json=payload)
            
            assert response.status_code == 500
            assert "Failed to upsert" in response.json()["detail"]

    def test_delete_endpoint_success(self, client):
        """Should delete vector and return success."""
        
        with patch("app.pinecone_service") as mock_pinecone_service:
            mock_pinecone_service.delete_vector.return_value = True
            
            payload = {
                "cloudinary_public_id": "img/photo1"
            }
            
            response = client.post("/delete-record", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["cloudinary_public_id"] == "img/photo1"
            
            mock_pinecone_service.delete_vector.assert_called_once_with(vector_id="img/photo1")

    def test_delete_endpoint_failure(self, client):
        """Should return 500 on delete failure."""
        
        with patch("app.pinecone_service") as mock_pinecone_service:
            mock_pinecone_service.delete_vector.return_value = False
            
            payload = {
                "cloudinary_public_id": "img/photo1"
            }
            
            response = client.post("/delete-record", json=payload)
            
            assert response.status_code == 500
            assert "Failed to delete" in response.json()["detail"]
