"""
Tests for label analytics endpoints.
"""

from __future__ import annotations

from server.database import Album, AlbumImage, Image, Label, db


def _create_sample_dataset():
    """Populate the database with albums, images, and labels for analytics tests."""
    album1 = Album(name="Album One", is_public=True)
    album2 = Album(name="Album Two", is_public=True)
    db.session.add_all([album1, album2])
    db.session.flush()

    image1 = Image(
        filename="image1.png",
        file_path="/tmp/image1.png",
        is_public=True,
        prompt="portrait painting",
    )
    image2 = Image(
        filename="image2.png",
        file_path="/tmp/image2.png",
        is_public=False,
        prompt="landscape vista",
    )
    image3 = Image(
        filename="image3.png",
        file_path="/tmp/image3.png",
        is_public=True,
        prompt="unlabeled concept",
    )
    db.session.add_all([image1, image2, image3])
    db.session.flush()

    db.session.add_all(
        [
            AlbumImage(album_id=album1.id, image_id=image1.id),
            AlbumImage(album_id=album1.id, image_id=image3.id),
            AlbumImage(album_id=album2.id, image_id=image2.id),
        ]
    )

    labels = [
        Label(image_id=image1.id, label_text="Portrait", label_type="manual"),
        Label(image_id=image1.id, label_text="portrait ", label_type="tag"),
        Label(image_id=image2.id, label_text="Portrait", label_type="tag"),
        Label(image_id=image2.id, label_text="Landscape", label_type="tag"),
        Label(image_id=image2.id, label_text="Landscape mood", label_type="manual"),
    ]
    db.session.add_all(labels)
    db.session.commit()

    return {
        "album1_id": album1.id,
        "album2_id": album2.id,
        "image1_id": image1.id,
        "image2_id": image2.id,
        "image3_id": image3.id,
    }


def test_label_stats_summary(client, app, mock_admin_auth):
    headers = {"Authorization": "Bearer admin_token"}
    with app.app_context():
        _create_sample_dataset()

    response = client.get("/api/labels/stats", headers=headers)
    assert response.status_code == 200
    data = response.get_json()

    assert data["total_labels"] == 5
    assert data["unique_labels"] == 3  # portrait, landscape, landscape mood
    assert data["images_with_labels"] == 2
    assert data["total_images"] == 3
    assert data["avg_labels_per_image"] == 2.5
    assert data["label_coverage_percent"] == 66.67

    assert data["by_type"]["tag"] == 3
    assert data["by_type"]["manual"] == 2

    top_tags = data["top_tags"]
    assert top_tags[0]["tag"] == "portrait"
    assert top_tags[0]["count"] == 3
    assert top_tags[0]["percentage"] == 60.0

    response_public = client.get("/api/labels/stats?public_only=true", headers=headers)
    assert response_public.status_code == 200
    public_data = response_public.get_json()
    assert public_data["total_labels"] == 2  # only labels on public image1
    assert public_data["total_images"] == 2  # image1 + image3
    assert public_data["images_with_labels"] == 1
    assert public_data["avg_labels_per_image"] == 2.0
    assert public_data["label_coverage_percent"] == 50.0


def test_label_top_tags_filtering(client, app, mock_admin_auth):
    headers = {"Authorization": "Bearer admin_token"}
    with app.app_context():
        _create_sample_dataset()

    response = client.get("/api/labels/top-tags?label_type=tag", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["total_labels"] == 3  # tag labels only
    tags = payload["results"]
    assert tags[0]["tag"] == "portrait"
    assert tags[0]["count"] == 2
    assert tags[0]["percentage"] == 66.67
    assert tags[1]["tag"] == "landscape"
    assert tags[1]["count"] == 1


def test_label_distribution(client, app, mock_admin_auth):
    headers = {"Authorization": "Bearer admin_token"}
    with app.app_context():
        _create_sample_dataset()

    response = client.get("/api/labels/distribution?page_size=10", headers=headers)
    assert response.status_code == 200
    data = response.get_json()

    assert data["total_albums"] == 2
    assert len(data["results"]) == 2

    first_album = data["results"][0]
    second_album = data["results"][1]

    # Album Two has the higher label count (3 labels on a single image)
    assert first_album["label_count"] == 3
    assert first_album["images_with_labels"] == 1
    assert first_album["label_coverage_percent"] == 100.0
    assert first_album["avg_labels_per_labeled_image"] == 3.0

    assert second_album["label_count"] == 2
    assert second_album["image_count"] == 2
    assert second_album["images_with_labels"] == 1
    assert second_album["label_coverage_percent"] == 50.0

    response_public = client.get("/api/labels/distribution?public_only=true", headers=headers)
    assert response_public.status_code == 200
    public_data = response_public.get_json()
    assert public_data["total_albums"] == 1
    assert len(public_data["results"]) == 1
    album = public_data["results"][0]
    assert album["label_count"] == 2
    assert album["image_count"] == 2
