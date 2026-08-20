from tests.conftest import auth_headers, register


def _make_discussion(client, published_course, author):
    topic = published_course.chapters[0].topics[0]
    res = client.post("/api/v1/discussions", json={"topic_id": str(topic.id), "title": "Discussion"}, headers=auth_headers(author))
    assert res.status_code == 201
    return res.json()["id"]


def test_comment_reply_and_tree_shape(client, published_course):
    author = register(client, "student")
    replier = register(client, "student")
    discussion_id = _make_discussion(client, published_course, author)

    top = client.post("/api/v1/comments", json={"discussion_id": discussion_id, "body": "Top level"}, headers=auth_headers(author))
    top_id = top.json()["id"]

    client.post(
        "/api/v1/comments",
        json={"discussion_id": discussion_id, "parent_comment_id": top_id, "body": "Reply"},
        headers=auth_headers(replier),
    )

    tree = client.get(f"/api/v1/discussions/{discussion_id}/comments").json()
    assert len(tree) == 1
    assert len(tree[0]["replies"]) == 1
    assert tree[0]["replies"][0]["body"] == "Reply"


def test_only_author_or_admin_can_edit_comment(client, published_course):
    author = register(client, "student")
    other = register(client, "student")
    discussion_id = _make_discussion(client, published_course, author)
    comment_id = client.post(
        "/api/v1/comments", json={"discussion_id": discussion_id, "body": "Mine"}, headers=auth_headers(author)
    ).json()["id"]

    forbidden = client.put(f"/api/v1/comments/{comment_id}", json={"body": "hacked"}, headers=auth_headers(other))
    assert forbidden.status_code == 403

    allowed = client.put(f"/api/v1/comments/{comment_id}", json={"body": "edited"}, headers=auth_headers(author))
    assert allowed.status_code == 200
    assert allowed.json()["body"] == "edited"


def test_delete_is_soft_and_masks_body_but_keeps_thread_shape(client, published_course):
    author = register(client, "student")
    replier = register(client, "student")
    discussion_id = _make_discussion(client, published_course, author)
    top_id = client.post(
        "/api/v1/comments", json={"discussion_id": discussion_id, "body": "Top"}, headers=auth_headers(author)
    ).json()["id"]
    client.post(
        "/api/v1/comments",
        json={"discussion_id": discussion_id, "parent_comment_id": top_id, "body": "Reply"},
        headers=auth_headers(replier),
    )

    client.delete(f"/api/v1/comments/{top_id}", headers=auth_headers(author))

    tree = client.get(f"/api/v1/discussions/{discussion_id}/comments").json()
    assert tree[0]["is_deleted"] is True
    assert tree[0]["body"] == "[deleted]"
    assert len(tree[0]["replies"]) == 1  # the reply is not orphaned


def test_vote_toggles_off_on_repeat(client, published_course):
    author = register(client, "student")
    voter = register(client, "student")
    discussion_id = _make_discussion(client, published_course, author)
    comment_id = client.post(
        "/api/v1/comments", json={"discussion_id": discussion_id, "body": "Vote me"}, headers=auth_headers(author)
    ).json()["id"]

    up = client.post(f"/api/v1/comments/{comment_id}/vote", json={"value": 1}, headers=auth_headers(voter))
    assert up.json()["vote_score"] == 1

    toggle_off = client.post(f"/api/v1/comments/{comment_id}/vote", json={"value": 1}, headers=auth_headers(voter))
    assert toggle_off.json()["vote_score"] == 0


def test_unauthenticated_user_cannot_comment(client, published_course):
    author = register(client, "student")
    discussion_id = _make_discussion(client, published_course, author)
    res = client.post("/api/v1/comments", json={"discussion_id": discussion_id, "body": "Anon"})
    assert res.status_code == 401
