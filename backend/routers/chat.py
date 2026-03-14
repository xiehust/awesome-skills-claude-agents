"""Chat SSE streaming API endpoints."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from schemas.message import ChatRequest, ChatSessionResponse, AnswerQuestionRequest, ChatMessageResponse
from database import db
from core.agent_manager import agent_manager
from core.session_manager import session_manager
from core.exceptions import (
    AgentNotFoundException,
    SessionNotFoundException,
    ValidationException,
    AgentExecutionException,
    AgentTimeoutException,
)
from middleware.tenant import TenantContext, get_tenant_context, require_role
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def create_sse_error(code: str, message: str, detail: str = None, suggested_action: str = None) -> str:
    """Create an SSE-formatted error event."""
    error_data = {
        "type": "error",
        "code": code,
        "message": message,
    }
    if detail:
        error_data["detail"] = detail
    if suggested_action:
        error_data["suggested_action"] = suggested_action
    return f"data: {json.dumps(error_data)}\n\n"


@router.post("/stream")
async def chat_stream(request: Request, ctx: TenantContext = Depends(get_tenant_context)):
    """Stream chat responses via SSE."""
    try:
        body = await request.json()
        chat_request = ChatRequest(**body)
    except json.JSONDecodeError as e:
        raise ValidationException(
            message="Invalid JSON format",
            detail=f"Failed to parse request body: {str(e)}",
        )
    except Exception as e:
        raise ValidationException(
            message="Invalid request data",
            detail=str(e),
        )

    # Verify agent exists (check tenant-owned or default)
    agent = await db.agents.get_with_tenant(chat_request.agent_id, ctx.tenant_id)
    if not agent:
        # Also allow the global default agent
        if chat_request.agent_id == "default":
            agent = await db.agents.get("default")
    if not agent:
        raise AgentNotFoundException(
            detail=f"Agent with ID '{chat_request.agent_id}' does not exist",
            suggested_action="Please check the agent ID and try again"
        )

    async def generate():
        try:
            logger.info(f"Starting chat stream for agent {chat_request.agent_id}")
            async for msg in agent_manager.run_conversation(
                agent_id=chat_request.agent_id,
                user_message=chat_request.message,
                session_id=chat_request.session_id,
                enable_skills=chat_request.enable_skills,
                enable_mcp=chat_request.enable_mcp,
                tenant_id=ctx.tenant_id,
            ):
                logger.debug(f"Yielding message: {msg.get('type')}")
                yield f"data: {json.dumps(msg)}\n\n"
        except asyncio.TimeoutError:
            logger.error("Agent response timed out")
            yield create_sse_error(
                code="AGENT_TIMEOUT",
                message="Agent response timed out. Your conversation has been saved.",
                suggested_action="Please try again"
            )
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            error_message = str(e)
            logger.error(f"Error in chat stream: {error_message}")
            logger.error(f"Full traceback:\n{error_traceback}")
            # Determine error type and provide appropriate response
            if "timeout" in error_message.lower():
                yield create_sse_error(
                    code="AGENT_TIMEOUT",
                    message="Agent response timed out. Your conversation has been saved.",
                    suggested_action="Please try again"
                )
            elif "connection" in error_message.lower() or "network" in error_message.lower():
                yield create_sse_error(
                    code="SERVICE_UNAVAILABLE",
                    message="Unable to connect to the AI service",
                    detail=error_message,
                    suggested_action="Please check your connection and try again"
                )
            else:
                yield create_sse_error(
                    code="AGENT_EXECUTION_ERROR",
                    message="Agent execution failed",
                    detail=f"{error_message}\n\nTraceback:\n{error_traceback}",
                    suggested_action="Please try again or contact support"
                )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/answer-question")
async def answer_question(request: Request, ctx: TenantContext = Depends(get_tenant_context)):
    """Continue chat by answering an AskUserQuestion via SSE.

    This endpoint is used when Claude asks the user a question via the
    AskUserQuestion tool. The frontend collects the user's answers and
    sends them here to continue the conversation.
    """
    try:
        body = await request.json()
        answer_request = AnswerQuestionRequest(**body)
    except json.JSONDecodeError as e:
        raise ValidationException(
            message="Invalid JSON format",
            detail=f"Failed to parse request body: {str(e)}",
        )
    except Exception as e:
        raise ValidationException(
            message="Invalid request data",
            detail=str(e),
        )

    # Verify agent exists (check tenant-owned or default)
    agent = await db.agents.get_with_tenant(answer_request.agent_id, ctx.tenant_id)
    if not agent:
        if answer_request.agent_id == "default":
            agent = await db.agents.get("default")
    if not agent:
        raise AgentNotFoundException(
            detail=f"Agent with ID '{answer_request.agent_id}' does not exist",
            suggested_action="Please check the agent ID and try again"
        )

    async def generate():
        try:
            logger.info(f"Answering question for agent {answer_request.agent_id}, session {answer_request.session_id}")
            async for msg in agent_manager.continue_with_answer(
                agent_id=answer_request.agent_id,
                session_id=answer_request.session_id,
                tool_use_id=answer_request.tool_use_id,
                answers=answer_request.answers,
                enable_skills=answer_request.enable_skills,
                enable_mcp=answer_request.enable_mcp,
                tenant_id=ctx.tenant_id,
            ):
                logger.debug(f"Yielding message: {msg.get('type')}")
                yield f"data: {json.dumps(msg)}\n\n"
        except asyncio.TimeoutError:
            logger.error("Agent response timed out")
            yield create_sse_error(
                code="AGENT_TIMEOUT",
                message="Agent response timed out. Your conversation has been saved.",
                suggested_action="Please try again"
            )
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            error_message = str(e)
            logger.error(f"Error in answer-question stream: {error_message}")
            logger.error(f"Full traceback:\n{error_traceback}")
            yield create_sse_error(
                code="AGENT_EXECUTION_ERROR",
                message="Agent execution failed",
                detail=f"{error_message}\n\nTraceback:\n{error_traceback}",
                suggested_action="Please try again or contact support"
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(agent_id: str | None = None, ctx: TenantContext = Depends(get_tenant_context)):
    """List chat sessions, optionally filtered by agent_id.

    Returns sessions sorted by last_accessed descending.
    """
    sessions = await session_manager.list_sessions(agent_id=agent_id, user_id=ctx.user_id)
    return [
        ChatSessionResponse(
            id=s.session_id,
            agent_id=s.agent_id,
            title=s.title,
            created_at=s.created_at,
            last_accessed_at=s.last_accessed,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(session_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Get a specific chat session by ID."""
    # Validate session belongs to tenant via the underlying DB record
    session_record = await db.sessions.get_with_tenant(session_id, ctx.tenant_id)
    if not session_record:
        raise SessionNotFoundException(
            detail=f"Session with ID '{session_id}' does not exist",
            suggested_action="Please check the session ID and try again"
        )
    return ChatSessionResponse(
        id=session_record.get("id", session_id),
        agent_id=session_record.get("agent_id", ""),
        title=session_record.get("title", ""),
        created_at=session_record.get("created_at", ""),
        last_accessed_at=session_record.get("last_accessed_at", ""),
    )


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_session_messages(session_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Get all messages for a chat session.

    Returns messages in chronological order.
    """
    # Verify session belongs to tenant
    session_record = await db.sessions.get_with_tenant(session_id, ctx.tenant_id)
    if not session_record:
        raise SessionNotFoundException(
            detail=f"Session with ID '{session_id}' does not exist",
            suggested_action="Please check the session ID and try again"
        )

    messages = await agent_manager.get_session_messages(session_id)
    return [
        ChatMessageResponse(
            id=msg.get("id"),
            session_id=msg.get("session_id"),
            role=msg.get("role"),
            content=msg.get("content", []),
            model=msg.get("model"),
            created_at=msg.get("created_at"),
        )
        for msg in messages
    ]


@router.post("/stop/{session_id}")
async def stop_session(session_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Stop a running chat session.

    This will interrupt the currently running agent for the given session.
    The agent will stop processing and the stream will end gracefully.
    """
    # Verify session belongs to tenant
    session_record = await db.sessions.get_with_tenant(session_id, ctx.tenant_id)
    if not session_record:
        return {"status": "not_found", "message": "Session not found"}

    logger.info(f"Received stop request for session {session_id}")
    result = await agent_manager.interrupt_session(session_id)

    if result["success"]:
        return {"status": "stopped", "message": result["message"]}
    else:
        # Return 200 even if session not found - client may have already finished
        return {"status": "not_found", "message": result["message"]}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    """Delete a chat session and all its messages."""
    # Verify session belongs to tenant
    session_record = await db.sessions.get_with_tenant(session_id, ctx.tenant_id)
    if not session_record:
        raise SessionNotFoundException(
            detail=f"Session with ID '{session_id}' does not exist",
            suggested_action="Please check the session ID and try again"
        )

    # First delete all messages for this session
    await db.messages.delete_by_session(session_id)

    # Then delete the session itself
    deleted = await session_manager.delete_session(session_id)
    if not deleted:
        raise SessionNotFoundException(
            detail=f"Session with ID '{session_id}' does not exist",
            suggested_action="Please check the session ID and try again"
        )
