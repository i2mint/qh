"""
Complete CRUD Example with Testing.

This is a comprehensive, real-world example demonstrating:
1. Full CRUD operations (Create, Read, Update, Delete)
2. Convention-based routing
3. Custom types with validation
4. Error handling
5. Comprehensive testing with pytest
6. Client generation
7. Integration testing

This example implements a simple blog API with users, posts, and comments.
"""

from qh import mk_app, register_json_type, mk_client_from_app
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


# ============================================================================
# Domain Models
# ============================================================================

class PostStatus(Enum):
    """Post publication status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass
@register_json_type
class User:
    """Blog user."""
    user_id: str
    username: str
    email: str
    full_name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
@register_json_type
class Post:
    """Blog post."""
    post_id: str
    author_id: str
    title: str
    content: str
    status: str = "draft"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'post_id': self.post_id,
            'author_id': self.author_id,
            'title': self.title,
            'content': self.content,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
@register_json_type
class Comment:
    """Comment on a blog post."""
    comment_id: str
    post_id: str
    author_id: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            'comment_id': self.comment_id,
            'post_id': self.post_id,
            'author_id': self.author_id,
            'content': self.content,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


# ============================================================================
# In-Memory Database
# ============================================================================

class BlogDatabase:
    """Simple in-memory database for the blog."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.posts: Dict[str, Post] = {}
        self.comments: Dict[str, Comment] = {}

    def reset(self):
        """Reset database (useful for testing)."""
        self.users.clear()
        self.posts.clear()
        self.comments.clear()


# Global database instance
db = BlogDatabase()


# ============================================================================
# User API Functions
# ============================================================================

def create_user(username: str, email: str, full_name: str) -> Dict:
    """
    Create a new user.

    Args:
        username: Unique username
        email: User email address
        full_name: User's full name

    Returns:
        Created user
    """
    # Validate uniqueness
    if any(u.username == username for u in db.users.values()):
        raise ValueError(f"Username '{username}' already exists")

    if any(u.email == email for u in db.users.values()):
        raise ValueError(f"Email '{email}' already exists")

    user = User(
        user_id=str(uuid.uuid4()),
        username=username,
        email=email,
        full_name=full_name
    )

    db.users[user.user_id] = user
    return user.to_dict()


def get_user(user_id: str) -> Dict:
    """
    Get a user by ID.

    Args:
        user_id: User ID

    Returns:
        User dict

    Raises:
        ValueError: If user not found
    """
    if user_id not in db.users:
        raise ValueError(f"User {user_id} not found")
    return db.users[user_id].to_dict()


def list_users(limit: int = 10, offset: int = 0) -> List[Dict]:
    """
    List users with pagination.

    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip

    Returns:
        List of user dicts
    """
    users = list(db.users.values())
    return [u.to_dict() for u in users[offset:offset + limit]]


def update_user(user_id: str, email: Optional[str] = None,
                full_name: Optional[str] = None) -> Dict:
    """
    Update user information.

    Args:
        user_id: User ID
        email: New email (optional)
        full_name: New full name (optional)

    Returns:
        Updated user
    """
    if user_id not in db.users:
        raise ValueError(f"User {user_id} not found")

    user = db.users[user_id]

    if email:
        user.email = email
    if full_name:
        user.full_name = full_name

    return user.to_dict()


def delete_user(user_id: str) -> Dict[str, str]:
    """
    Delete a user.

    Args:
        user_id: User ID

    Returns:
        Confirmation message
    """
    if user_id not in db.users:
        raise ValueError(f"User {user_id} not found")

    del db.users[user_id]
    return {'message': f'User {user_id} deleted', 'user_id': user_id}


# ============================================================================
# Post API Functions
# ============================================================================

def create_post(author_id: str, title: str, content: str,
                tags: Optional[List[str]] = None) -> Dict:
    """
    Create a new blog post.

    Args:
        author_id: ID of the post author
        title: Post title
        content: Post content
        tags: Optional list of tags

    Returns:
        Created post
    """
    # Verify author exists
    if author_id not in db.users:
        raise ValueError(f"Author {author_id} not found")

    post = Post(
        post_id=str(uuid.uuid4()),
        author_id=author_id,
        title=title,
        content=content,
        tags=tags or []
    )

    db.posts[post.post_id] = post
    return post.to_dict()


def get_post(post_id: str) -> Dict:
    """Get a post by ID."""
    if post_id not in db.posts:
        raise ValueError(f"Post {post_id} not found")
    return db.posts[post_id]


def list_posts(author_id: Optional[str] = None, status: Optional[str] = None,
               limit: int = 10, offset: int = 0) -> List[Dict]:
    """
    List posts with filtering and pagination.

    Args:
        author_id: Filter by author (optional)
        status: Filter by status (optional)
        limit: Maximum posts to return
        offset: Number of posts to skip

    Returns:
        List of posts
    """
    posts = list(db.posts.values())

    # Apply filters
    if author_id:
        posts = [p for p in posts if p.author_id == author_id]
    if status:
        posts = [p for p in posts if p.status == status]

    # Sort by created_at descending (newest first)
    posts.sort(key=lambda p: p.created_at, reverse=True)

    return [p.to_dict() for p in posts[offset:offset + limit]]


def update_post(post_id: str, title: Optional[str] = None,
                content: Optional[str] = None, status: Optional[str] = None,
                tags: Optional[List[str]] = None) -> Dict:
    """
    Update a blog post.

    Args:
        post_id: Post ID
        title: New title (optional)
        content: New content (optional)
        status: New status (optional)
        tags: New tags (optional)

    Returns:
        Updated post
    """
    if post_id not in db.posts:
        raise ValueError(f"Post {post_id} not found")

    post = db.posts[post_id]

    if title:
        post.title = title
    if content:
        post.content = content
    if status:
        if status not in [s.value for s in PostStatus]:
            raise ValueError(f"Invalid status: {status}")
        post.status = status
    if tags is not None:
        post.tags = tags

    post.updated_at = datetime.now().isoformat()

    return post.to_dict()


def delete_post(post_id: str) -> Dict[str, str]:
    """Delete a post."""
    if post_id not in db.posts:
        raise ValueError(f"Post {post_id} not found")

    # Also delete associated comments
    comment_ids = [c_id for c_id, c in db.comments.items() if c.post_id == post_id]
    for c_id in comment_ids:
        del db.comments[c_id]

    del db.posts[post_id]
    return {
        'message': f'Post {post_id} deleted',
        'post_id': post_id,
        'comments_deleted': len(comment_ids)
    }


# ============================================================================
# Comment API Functions
# ============================================================================

def create_comment(post_id: str, author_id: str, content: str) -> Dict:
    """Create a comment on a post."""
    if post_id not in db.posts:
        raise ValueError(f"Post {post_id} not found")
    if author_id not in db.users:
        raise ValueError(f"Author {author_id} not found")

    comment = Comment(
        comment_id=str(uuid.uuid4()),
        post_id=post_id,
        author_id=author_id,
        content=content
    )

    db.comments[comment.comment_id] = comment
    return comment.to_dict()


def list_comments_for_post(post_id: str) -> List[Dict]:
    """List all comments for a post."""
    if post_id not in db.posts:
        raise ValueError(f"Post {post_id} not found")

    comments = [c for c in db.comments.values() if c.post_id == post_id]
    comments.sort(key=lambda c: c.created_at)
    return [c.to_dict() for c in comments]


def delete_comment(comment_id: str) -> Dict[str, str]:
    """Delete a comment."""
    if comment_id not in db.comments:
        raise ValueError(f"Comment {comment_id} not found")

    del db.comments[comment_id]
    return {'message': f'Comment {comment_id} deleted', 'comment_id': comment_id}


# ============================================================================
# Statistics Functions
# ============================================================================

def get_blog_stats() -> Dict[str, int]:
    """Get overall blog statistics."""
    return {
        'total_users': len(db.users),
        'total_posts': len(db.posts),
        'total_comments': len(db.comments),
        'published_posts': len([p for p in db.posts.values() if p.status == 'published']),
        'draft_posts': len([p for p in db.posts.values() if p.status == 'draft'])
    }


def get_user_stats(user_id: str) -> Dict[str, any]:
    """Get statistics for a specific user."""
    if user_id not in db.users:
        raise ValueError(f"User {user_id} not found")

    user = db.users[user_id]
    posts = [p for p in db.posts.values() if p.author_id == user_id]
    comments = [c for c in db.comments.values() if c.author_id == user_id]

    return {
        'user_id': user_id,
        'username': user.username,
        'total_posts': len(posts),
        'published_posts': len([p for p in posts if p.status == 'published']),
        'total_comments': len(comments)
    }


# ============================================================================
# Create the App
# ============================================================================

# Group functions by resource
user_functions = [create_user, get_user, list_users, update_user, delete_user]
post_functions = [create_post, get_post, list_posts, update_post, delete_post]
comment_functions = [create_comment, list_comments_for_post, delete_comment]
stats_functions = [get_blog_stats, get_user_stats]

all_functions = user_functions + post_functions + comment_functions + stats_functions

# Create app with conventions
app = mk_app(all_functions, use_conventions=True, title="Blog API", version="1.0.0")


# ============================================================================
# Testing with pytest
# ============================================================================

def test_user_crud():
    """Test complete user CRUD operations."""
    db.reset()
    client = mk_client_from_app(app)

    # Create user
    user = client.create_user(
        username="johndoe",
        email="john@example.com",
        full_name="John Doe"
    )
    assert user['username'] == "johndoe"
    assert 'user_id' in user

    user_id = user['user_id']

    # Get user
    fetched = client.get_user(user_id=user_id)
    assert fetched['username'] == "johndoe"

    # List users
    users = client.list_users(limit=10, offset=0)
    assert len(users) == 1

    # Update user
    updated = client.update_user(user_id=user_id, full_name="John Updated Doe")
    assert updated['full_name'] == "John Updated Doe"

    # Delete user
    result = client.delete_user(user_id=user_id)
    assert result['user_id'] == user_id

    print("✓ User CRUD tests passed")


def test_post_crud():
    """Test complete post CRUD operations."""
    db.reset()
    client = mk_client_from_app(app)

    # Create user first
    user = client.create_user(
        username="author1",
        email="author@example.com",
        full_name="Test Author"
    )
    user_id = user['user_id']

    # Create post
    post = client.create_post(
        author_id=user_id,
        title="My First Post",
        content="This is the content",
        tags=["tech", "python"]
    )
    assert post['title'] == "My First Post"
    assert post['tags'] == ["tech", "python"]

    post_id = post['post_id']

    # Get post
    fetched = client.get_post(post_id=post_id)
    assert fetched['title'] == "My First Post"

    # List posts
    posts = client.list_posts(author_id=user_id, limit=10, offset=0)
    assert len(posts) == 1

    # Update post
    updated = client.update_post(
        post_id=post_id,
        status="published",
        title="My Updated Post"
    )
    assert updated['status'] == "published"
    assert updated['title'] == "My Updated Post"

    # Delete post
    result = client.delete_post(post_id=post_id)
    assert result['post_id'] == post_id

    print("✓ Post CRUD tests passed")


def test_comments():
    """Test comment operations."""
    db.reset()
    client = mk_client_from_app(app)

    # Setup: create user and post
    user = client.create_user(
        username="commenter",
        email="commenter@example.com",
        full_name="Comment User"
    )
    user_id = user['user_id']

    post = client.create_post(
        author_id=user_id,
        title="Test Post",
        content="Test content"
    )
    post_id = post['post_id']

    # Create comment
    comment = client.create_comment(
        post_id=post_id,
        author_id=user_id,
        content="Great post!"
    )
    assert comment['content'] == "Great post!"

    # List comments
    comments = client.list_comments_for_post(post_id=post_id)
    assert len(comments) == 1

    # Delete comment
    result = client.delete_comment(comment_id=comment['comment_id'])
    assert 'comment_id' in result

    print("✓ Comment tests passed")


def test_statistics():
    """Test statistics functions."""
    db.reset()
    client = mk_client_from_app(app)

    # Create test data
    user = client.create_user(
        username="statuser",
        email="stats@example.com",
        full_name="Stats User"
    )
    user_id = user['user_id']

    client.create_post(
        author_id=user_id,
        title="Post 1",
        content="Content 1"
    )

    client.create_post(
        author_id=user_id,
        title="Post 2",
        content="Content 2"
    )

    # Get blog stats
    blog_stats = client.get_blog_stats()
    assert blog_stats['total_users'] == 1
    assert blog_stats['total_posts'] == 2

    # Get user stats
    user_stats = client.get_user_stats(user_id=user_id)
    assert user_stats['total_posts'] == 2

    print("✓ Statistics tests passed")


def test_error_handling():
    """Test that errors are handled correctly."""
    db.reset()
    client = mk_client_from_app(app)

    # Test getting non-existent user
    try:
        client.get_user(user_id="nonexistent")
        assert False, "Should have raised error"
    except Exception as e:
        # Check response text if available
        error_text = e.response.text if hasattr(e, 'response') else str(e)
        assert "not found" in error_text.lower()

    # Test creating duplicate username
    client.create_user(
        username="duplicate",
        email="dup1@example.com",
        full_name="Dup User"
    )

    try:
        client.create_user(
            username="duplicate",  # Same username
            email="dup2@example.com",
            full_name="Dup User 2"
        )
        assert False, "Should have raised error for duplicate username"
    except Exception as e:
        error_text = e.response.text if hasattr(e, 'response') else str(e)
        assert "already exists" in error_text.lower()

    print("✓ Error handling tests passed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Running Blog API Tests")
    print("=" * 70 + "\n")

    tests = [
        test_user_crud,
        test_post_crud,
        test_comments,
        test_statistics,
        test_error_handling,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")

    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    from qh import print_routes

    print("\n" + "=" * 70)
    print("Blog API - Complete CRUD Example")
    print("=" * 70)

    print("\nAvailable Routes:")
    print("-" * 70)
    print_routes(app)

    print("\n" + "=" * 70)
    print("Running Tests")
    print("=" * 70)

    run_all_tests()

    print("\n" + "=" * 70)
    print("To start the server:")
    print("=" * 70)
    print("\n  uvicorn examples.complete_crud_example:app --reload\n")
    print("Then visit:")
    print("  • http://localhost:8000/docs - Interactive API documentation")
    print("  • http://localhost:8000/redoc - Alternative documentation")
    print("  • http://localhost:8000/openapi.json - OpenAPI specification")
    print("\n" + "=" * 70 + "\n")
