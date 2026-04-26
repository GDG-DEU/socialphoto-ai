import pytest
from unittest.mock import MagicMock, patch
import os

@pytest.fixture
def mock_pinecone_client():
    with patch("src.services.pinecone_service.Pinecone") as mock_pinecone:
        mock_index_instance = MagicMock()
        mock_pinecone_instance = mock_pinecone.return_value
        
        # Mock list_indexes
        mock_index_record = MagicMock()
        mock_index_record.name = "test-index"
        mock_pinecone_instance.list_indexes.return_value = [mock_index_record]
        
        # Mock Index
        mock_pinecone_instance.Index.return_value = mock_index_instance
        
        yield mock_pinecone, mock_pinecone_instance, mock_index_instance

@patch.dict(os.environ, {"PINECONE_API_KEY": "fake-key", "PINECONE_INDEX_NAME": "test-index"})
def test_pinecone_init_success(mock_pinecone_client):
    mock_class, mock_instance, mock_index = mock_pinecone_client
    
    from src.services.pinecone_service import PineconeService
    service = PineconeService()
    
    assert service.pc is not None
    assert service.index is not None
    mock_class.assert_called_once_with(api_key="fake-key")
    mock_instance.Index.assert_called_once_with("test-index")

@patch.dict(os.environ, {"PINECONE_API_KEY": "fake-key", "PINECONE_INDEX_NAME": "missing-index"})
def test_pinecone_init_index_not_found(mock_pinecone_client):
    mock_class, mock_instance, mock_index = mock_pinecone_client
    
    # Override list_indexes to return names that don't match
    mock_index_record = MagicMock()
    mock_index_record.name = "other-index"
    mock_instance.list_indexes.return_value = [mock_index_record]
    
    from src.services.pinecone_service import PineconeService
    service = PineconeService()
    
    assert service.pc is not None
    assert service.index is None # Should be none if index verification fails

@patch.dict(os.environ, {"PINECONE_API_KEY": "fake-key", "PINECONE_INDEX_NAME": "test-index"})
def test_upsert_vectors_success(mock_pinecone_client):
    _, _, mock_index = mock_pinecone_client
    from src.services.pinecone_service import PineconeService
    service = PineconeService()

    mock_response = MagicMock()
    mock_response.upserted_count = 1
    mock_index.upsert.return_value = mock_response

    vectors = [("vec1", [0.1, 0.2], {"meta": "data"})]
    result = service.upsert_vectors(vectors)

    assert result is True
    mock_index.upsert.assert_called_once()
    _, kwargs = mock_index.upsert.call_args
    # SDK v3 expects dicts, not tuples
    assert kwargs['vectors'] == [{"id": "vec1", "values": [0.1, 0.2], "metadata": {"meta": "data"}}]

@patch.dict(os.environ, {"PINECONE_API_KEY": "fake-key", "PINECONE_INDEX_NAME": "test-index"})
def test_upsert_vectors_fails_when_upserted_count_zero(mock_pinecone_client):
    _, _, mock_index = mock_pinecone_client
    from src.services.pinecone_service import PineconeService
    service = PineconeService()

    mock_response = MagicMock()
    mock_response.upserted_count = 0
    mock_index.upsert.return_value = mock_response

    vectors = [("vec1", [0.1, 0.2], {"meta": "data"})]
    result = service.upsert_vectors(vectors)

    assert result is False

@patch.dict(os.environ, {"PINECONE_API_KEY": "fake-key", "PINECONE_INDEX_NAME": "test-index"})
def test_delete_vector_success(mock_pinecone_client):
    _, _, mock_index = mock_pinecone_client
    from src.services.pinecone_service import PineconeService
    service = PineconeService()
    
    result = service.delete_vector("vec1")
    
    assert result is True
    mock_index.delete.assert_called_once_with(ids=["vec1"])

@patch.dict(os.environ, {"PINECONE_API_KEY": "fake-key", "PINECONE_INDEX_NAME": "test-index"})
def test_query_vectors_success(mock_pinecone_client):
    _, _, mock_index = mock_pinecone_client

    # SDK v3 returns an object with .matches attribute, not a dict
    mock_match = MagicMock()
    mock_match.id = "vec1"
    mock_match.score = 0.9
    mock_match.metadata = {"cloudinary_public_id": "img/photo1"}

    mock_response = MagicMock()
    mock_response.matches = [mock_match]
    mock_index.query.return_value = mock_response

    from src.services.pinecone_service import PineconeService
    service = PineconeService()
    results = service.query_vectors([0.1, 0.2])

    assert len(results) == 1
    assert results[0]["id"] == "vec1"
    assert results[0]["score"] == 0.9
    assert results[0]["metadata"]["cloudinary_public_id"] == "img/photo1"
    mock_index.query.assert_called_once()
