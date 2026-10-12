from django.urls import path

from . import views

urlpatterns = [
    path("feed", views.FeedView.as_view(), name="feed"),
    path("posts", views.PostCreateView.as_view(), name="post-create"),
    path("posts/<uuid:post_id>", views.PostView.as_view(), name="post"),
    path("posts/<uuid:post_id>/like", views.LikeView.as_view(), name="post-like"),
    path("posts/<uuid:post_id>/save", views.SaveView.as_view(), name="post-save"),
    path("posts/<uuid:post_id>/share", views.ShareView.as_view(), name="post-share"),
    path("posts/<uuid:post_id>/comments", views.CommentsView.as_view(), name="post-comments"),
    path("comments/<uuid:comment_id>", views.CommentView.as_view(), name="comment"),
    path("me/posts", views.MyPostsView.as_view(), name="my-posts"),
    path("me/saved", views.SavedPostsView.as_view(), name="my-saved"),
    path("me/following", views.FollowingView.as_view(), name="my-following"),
    path("people/<uuid:user_id>/posts", views.PersonPostsView.as_view(), name="person-posts"),
    path("people/<uuid:user_id>/follow", views.FollowView.as_view(), name="person-follow"),
    path("stories", views.StoriesView.as_view(), name="stories"),
    path("stories/<uuid:story_id>", views.StoryDetailView.as_view(), name="story"),
    path("stories/<uuid:story_id>/seen", views.StorySeenView.as_view(), name="story-seen"),
    path("pros/<slug:slug>/reviews", views.ProReviewsView.as_view(), name="pro-reviews"),
    path("reviews", views.ReviewCreateView.as_view(), name="review-create"),
    path("reviews/<uuid:review_id>/reply", views.ReviewReplyView.as_view(), name="review-reply"),
    path("me/reviews/pending", views.PendingReviewsView.as_view(), name="my-pending-reviews"),
    path("me/pro/client-ratings", views.ClientRatingView.as_view(), name="client-rating"),
]
