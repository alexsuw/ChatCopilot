import logging
import asyncio
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from postgrest.exceptions import APIError

from src.settings import settings

# --- Supabase Client Initialization ---
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_anon_key.get_secret_value()
)

# --- Helper Functions ---

async def create_user(user_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
    """Create or update user in the database"""
    try:
        user_data = {"id": user_id}
        if username:
            user_data["username"] = username
        if first_name:
            user_data["first_name"] = first_name
            
        result = supabase.table("users").upsert(user_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error creating/updating user: {e}")
        raise e

async def create_team(name: str, admin_id: int, invite_code: str, system_message: str = None) -> Dict[str, Any]:
    """Create a new team"""
    try:
        team_data = {
            "name": name,
            "admin_id": admin_id,
            "invite_code": invite_code
        }
        if system_message:
            team_data["system_message"] = system_message
            
        result = supabase.table("teams").insert(team_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error creating team: {e}")
        raise e

async def get_team_by_invite_code(invite_code: str) -> Optional[Dict[str, Any]]:
    """Get team by invite code"""
    try:
        result = supabase.table("teams").select("*").eq("invite_code", invite_code).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error getting team by invite code: {e}")
        return None

async def get_team_by_id(team_id: str) -> Optional[Dict[str, Any]]:
    """Get team by ID"""
    try:
        result = supabase.table("teams").select("*").eq("id", team_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error getting team by ID: {e}")
        return None

async def update_team_system_message(team_id: str, system_message: str) -> Optional[Dict[str, Any]]:
    """Update team system message"""
    try:
        result = supabase.table("teams").update({"system_message": system_message}).eq("id", team_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error updating team system message: {e}")
        raise e

async def add_user_to_team(user_id: int, team_id: str, role: str = "member") -> Dict[str, Any]:
    """Add user to team with specified role"""
    try:
        user_team_data = {
            "user_id": user_id,
            "team_id": team_id,
            "role": role
        }
        result = supabase.table("user_teams").upsert(user_team_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error adding user to team: {e}")
        raise e

async def get_user_teams(user_id: int) -> List[Dict[str, Any]]:
    """Get all teams where user is a member"""
    try:
        result = supabase.table("user_teams")\
            .select("teams(*)")\
            .eq("user_id", user_id)\
            .execute()
        
        teams = []
        for item in result.data:
            if item.get("teams"):
                teams.append(item["teams"])
        return teams
    except Exception as e:
        logging.error(f"Error getting user teams: {e}")
        return []

async def get_user_admin_teams(user_id: int) -> List[Dict[str, Any]]:
    """Get all teams where user is an admin"""
    try:
        result = supabase.table("user_teams")\
            .select("teams(*)")\
            .eq("user_id", user_id)\
            .eq("role", "admin")\
            .execute()
        
        teams = []
        for item in result.data:
            if item.get("teams"):
                teams.append(item["teams"])
        return teams
    except Exception as e:
        logging.error(f"Error getting user admin teams: {e}")
        return []

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error getting user by ID: {e}")
        return None

async def link_chat_to_team(chat_id: int, team_id: str, title: str = None) -> Dict[str, Any]:
    """Link a chat to a team"""
    try:
        chat_data = {
            "id": chat_id,
            "team_id": team_id
        }
        if title:
            chat_data["title"] = title
            
        result = supabase.table("linked_chats").upsert(chat_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error linking chat to team: {e}")
        raise e

async def get_linked_chat(chat_id: int) -> Optional[Dict[str, Any]]:
    """Get linked chat by chat ID"""
    try:
        result = supabase.table("linked_chats").select("*").eq("id", chat_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logging.error(f"Error getting linked chat: {e}")
        return None

def init_supabase():
    """
    Initialize Supabase connection (placeholder for future initialization logic)
    """
    try:
        # Test connection
        supabase.table("teams").select("count", count="exact").execute()
        logging.info("Supabase connection initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing Supabase: {e}")
        raise e 