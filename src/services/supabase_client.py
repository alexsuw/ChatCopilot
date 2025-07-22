import logging
import asyncio
from typing import Optional, List, Dict, Any
from supabase import create_client, Client

# Initialize Supabase client
supabase: Client = None

async def get_team_by_id(team_id: str) -> Optional[Dict]:
    """Get team document by ID"""
    try:
        result = supabase.table("teams").select("*").eq("id", team_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logging.error(f"Error getting team {team_id}: {e}")
        return None

async def get_teams_by_user(user_id: int) -> List[Dict]:
    """Get all teams where user is a member"""
    try:
        result = supabase.table("team_members").select("""
            teams (
                id,
                name,
                description,
                created_at
            )
        """).eq("user_id", user_id).execute()
        
        teams = []
        if result.data:
            for item in result.data:
                if item.get('teams'):
                    teams.append(item['teams'])
        
        return teams
    except Exception as e:
        logging.error(f"Error getting teams for user {user_id}: {e}")
        return []

async def create_team(name: str, description: str, creator_id: int, system_message: str = None) -> Optional[str]:
    """Create a new team and return team ID"""
    try:
        # Create team
        team_data = {
            "name": name,
            "description": description,
            "creator_id": creator_id
        }
        
        if system_message:
            team_data["system_message"] = system_message
            
        team_result = supabase.table("teams").insert(team_data).execute()
        
        if not team_result.data:
            logging.error("Failed to create team - no data returned")
            return None
            
        team_id = team_result.data[0]['id']
        
        # Add creator as team member
        member_data = {
            "team_id": team_id,
            "user_id": creator_id,
            "role": "owner"
        }
        
        member_result = supabase.table("team_members").insert(member_data).execute()
        
        if not member_result.data:
            logging.error(f"Failed to add creator as team member for team {team_id}")
            # Should we rollback team creation here?
        
        logging.info(f"Created team {team_id} with owner {creator_id}")
        return team_id
        
    except Exception as e:
        logging.error(f"Error creating team: {e}")
        return None

async def update_team_system_message(team_id: str, system_message: str, user_id: int) -> bool:
    """Update team's system message (only for team members)"""
    try:
        # Check if user is team member
        member_check = supabase.table("team_members").select("role").eq("team_id", team_id).eq("user_id", user_id).execute()
        
        if not member_check.data:
            logging.warning(f"User {user_id} is not a member of team {team_id}")
            return False
        
        # Update system message
        result = supabase.table("teams").update({"system_message": system_message}).eq("id", team_id).execute()
        
        if result.data:
            logging.info(f"Updated system message for team {team_id} by user {user_id}")
            return True
        return False
        
    except Exception as e:
        logging.error(f"Error updating system message for team {team_id}: {e}")
        return False

async def delete_team(team_id: str, user_id: int) -> bool:
    """Delete team (only for team owners)"""
    try:
        # Check if user is team owner
        owner_check = supabase.table("team_members").select("role").eq("team_id", team_id).eq("user_id", user_id).eq("role", "owner").execute()
        
        if not owner_check.data:
            logging.warning(f"User {user_id} is not an owner of team {team_id}")
            return False
        
        # Delete team (this should cascade delete members and linked chats)
        result = supabase.table("teams").delete().eq("id", team_id).execute()
        
        if result.data:
            logging.info(f"Deleted team {team_id} by owner {user_id}")
            return True
        return False
        
    except Exception as e:
        logging.error(f"Error deleting team {team_id}: {e}")
        return False

async def link_chat_to_team(chat_id: int, chat_title: str, team_id: str, user_id: int) -> bool:
    """Link a chat to a team (only for team members)"""
    try:
        # Check if user is team member
        member_check = supabase.table("team_members").select("role").eq("team_id", team_id).eq("user_id", user_id).execute()
        
        if not member_check.data:
            logging.warning(f"User {user_id} is not a member of team {team_id}")
            return False
        
        # Check if chat is already linked
        existing_link = supabase.table("linked_chats").select("*").eq("chat_id", chat_id).execute()
        
        if existing_link.data:
            # Update existing link
            result = supabase.table("linked_chats").update({
                "team_id": team_id,
                "chat_title": chat_title
            }).eq("chat_id", chat_id).execute()
        else:
            # Create new link
            link_data = {
                "chat_id": chat_id,
                "chat_title": chat_title,
                "team_id": team_id,
                "linked_by": user_id
            }
            result = supabase.table("linked_chats").insert(link_data).execute()
        
        if result.data:
            logging.info(f"Linked chat {chat_id} to team {team_id} by user {user_id}")
            return True
        return False
        
    except Exception as e:
        logging.error(f"Error linking chat {chat_id} to team {team_id}: {e}")
        return False

async def get_linked_chat(chat_id: int) -> Optional[Dict]:
    """Get linked chat info"""
    try:
        result = supabase.table("linked_chats").select("*").eq("chat_id", chat_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logging.error(f"Error getting linked chat {chat_id}: {e}")
        return None

async def get_team_linked_chats(team_id: str) -> List[Dict]:
    """Get all chats linked to a team"""
    try:
        result = supabase.table("linked_chats").select("*").eq("team_id", team_id).execute()
        return result.data if result.data else []
    except Exception as e:
        logging.error(f"Error getting linked chats for team {team_id}: {e}")
        return []

async def save_message(team_id: str, chat_id: int, message_id: int, user_id: int, user_name: str, text: str) -> None:
    """Save a message to the database"""
    try:
        message_data = {
            "team_id": team_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "user_id": user_id,
            "user_name": user_name,
            "text": text,
        }
        supabase.table("messages").insert(message_data).execute()
        logging.info(f"Saved message from user {user_id} in chat {chat_id} to team {team_id}")
    except Exception as e:
        logging.error(f"Error saving message: {e}")
        # We don't re-raise here to not break the bot on a single message save failure
        pass

async def search_messages_by_text(team_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for messages using full-text search"""
    try:
        # 'websearch_to_tsquery' is generally better for user-provided search terms
        result = supabase.rpc(
            "match_messages",
            {"team_id_filter": team_id, "query": query, "match_limit": limit}
        ).execute()
        return result.data if result.data else []
    except Exception as e:
        logging.error(f"Error searching messages: {e}")
        return []

def init_supabase(url: str, key: str):
    """Initialize Supabase client"""
    global supabase
    try:
        supabase = create_client(url, key)
        logging.info("✅ Supabase client initialized successfully")
    except Exception as e:
        logging.error(f"❌ Failed to initialize Supabase client: {e}")
        raise e