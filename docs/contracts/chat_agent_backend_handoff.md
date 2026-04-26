# AI Chat Integration Handoff (Backend ↔ AI Service)

## Scope
This document defines the production chat integration contract between Node.js backend and AI Service.

## Core Behavior
- AI Service is stateless per request.
- AI Service returns user-facing text in `ChatResponse.reply` and backend-facing tool payloads in `ChatResponse.actions`.
- Cloudinary public IDs and similar internal references are separated into `actions` for backend consumption; user-facing text is sanitized.
- AI Service does not write/read chat history from DB.
- Node.js backend owns message persistence, session state, and conversation management.

## AI Service Chat Endpoint
- Method: `POST /chat`
- Auth: existing API key mechanism (already implemented in AI Service)

### Request (`ChatRequest`)
```json
{
  "user_id": "string",
  "message": "string",
  "history": [
    {
      "role": "USER | ASSISTANT",
      "content": "string",
      "tool_calls": {
        "cloudinary_public_id": "chat-temp/abc123"
      }
    }
  ],
  "cloudinary_public_id": "optional-string"
}
```

### Response (`ChatResponse`)
```json
{
  "reply": "string",
  "actions": [
    {
      "type": "search_similar_images_result",
      "parameters": {
        "cloudinary_public_ids": ["chat-temp/abc123", "gallery/def456"],
        "result": {
          "results": [
            {"cloudinary_public_id": "chat-temp/abc123", "sim_score": 0.98}
          ]
        }
      }
    }
  ]
}
```

`actions` may be `null` when no tool output is needed.

## History Mapping Rules
- `role: USER` maps to Gemini `user`.
- `role: ASSISTANT` maps to Gemini `model`.
- If `tool_calls.cloudinary_public_id` exists, AI Service fetches that image from Cloudinary and includes it in the model input.
- Current-turn image is passed via `cloudinary_public_id`.

## Agent Tools Used by AI Service
1. `search_similar_images`
- Uses existing similarity search service.
- Inputs: `query_text?`, `cloudinary_public_id?`, `top_k` (default `5`).
- Backend receives tool output via `actions` with:
  - `type: search_similar_images_result`
  - `parameters.cloudinary_public_ids`
  - `parameters.result`

2. `get_user_context`
- AI Service calls Node.js internal endpoint:
- `GET {BACKEND_URL}/internal/users/{user_id}/context`
- Header: `X-API-Key: {API_KEY}`

## Backend Endpoint Requirement
Node.js must expose:
- `GET /internal/users/:user_id/context`
- Must return user profile + recent-post context JSON for personalization.

## Environment Requirements (AI Service)
- `GEMINI_API_KEY=`
- `BACKEND_URL=`
- `API_KEY=` (already used for internal auth header)

## Failure/Guardrails
- Tool loop max rounds: `5`.
- If loop fails to complete, AI Service returns:
- `I'm having trouble completing your request. Please try again.`
