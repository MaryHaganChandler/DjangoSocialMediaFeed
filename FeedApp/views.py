from django.shortcuts import render, redirect
from .forms import PostForm,ProfileForm, RelationshipForm
from .models import Post, Comment, Like, Profile, Relationship
from datetime import datetime, date

from django.contrib.auth.decorators import login_required
from django.http import Http404


# Create your views here.

# When a URL request matches the pattern we just defined, 
# Django looks for a function called index() in the views.py file. 

def index(request):
    """The home page for Learning Log."""
    return render(request, 'FeedApp/index.html')



@login_required     #This is called a decorator, and it prevents unauthorized access
def profile(request):
    profile = Profile.objects.filter(user = request.user)
        #request.user refers to the person currently logged on and using the system
        #"user" is one of the fields in Profile
    #See if user already has a profile. If not, create one.
    if not profile.exists():
        Profile.objects.create(user = request.user)
    profile = Profile.objects.get(user = request.user)

    if request.method != 'POST':
        form = ProfileForm(instance = profile)
    else:
        form = ProfileForm(instance = profile, data = request.POST)
        if form.is_valid():
            form.save()
            return redirect('FeedApp:profile')

    context = {'form':form}
    return render(request, 'FeedApp/profile.html', context)

@login_required
def myfeed(request):
    comment_count_list = []
    like_count_list = []
    posts = Post.objects.filter(username = request.user).order_by('-date_posted')
        #If you only had one post, you could use get(), but you need to
        #   use filter() if you have more than one.
    for p in posts:
        c_count = Comment.objects.filter(post = p).count()  #Counts the # of comments
        l_count = Like.objects.filter(post = p).count()     #Counts the # of likes
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts, comment_count_list, like_count_list)

    context = {'posts':posts, 'zipped_list':zipped_list}
    return render(request, 'FeedApp/myfeed.html', context)
    
@login_required
def new_post(request):
    #See if this is a get or post request. If it's a get request, we want to load an
    #   empty form for the user to fill out to create a new post, or if it's a post
    #   request, whatever the user filled out we want to save to the database.
    if request.method != 'POST':
        form = PostForm()   #load as a blank form
    else:
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            new_post = form.save(commit = False)
            new_post.username = request.user    #The person using the system is the poster
            new_post.save()
            return redirect('FeedApp:myfeed')   #Let the person view their post
    context = {'form':form}
    return render(request, 'FeedApp/new_post.html', context)

@login_required
def friendsfeed(request):
    comment_count_list = []
    like_count_list = []
    friends = Profile.objects.filter(user=request.user).values('friends')
    posts = Post.objects.filter(username__in=friends).order_by('-date_posted')
    for p in posts:
        c_count = Comment.objects.filter(post = p).count()
        l_count = Like.objects.filter(post = p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts, comment_count_list, like_count_list)

    #Check to see if the like button was clicked.
    if request.method == 'POST' and request.POST.get("like"):
        post_to_like = request.POST.get("like")     #Get the ID of the like button
        print(post_to_like)
        like_already_exists = Like.objects.filter(post_id= post_to_like, username =request.user)
            #Make sure the same user doesn't like the same post more than once.
        if not like_already_exists():
            Like.objects.create(post_id = post_to_like, username = request.user)
            return redirect("FeedApp:friendsfeed") #refreshes the page with the updated content




    context = {'posts': posts, 'zipped_list': zipped_list}
    return render(request, 'FeedApp/friendsfeed.html', context)





@login_required
def comments(request, post_id):
    #We want the "comments" to be a link, so we're going to make our own button (we don't
    #   want to do it automatically through html since we'll then need to make another form)
    #Check to see if a button has been pressed on the page.
    if request.method == 'POST' and request.POST.get("btn1"):
        comment = request.POST.get("comment")   #We're getting the text in the box
        #Create a new row in the comment model.
        Comment.objects.create(post_id = post_id, username=request.user, text= comment, date_added = date.today())
            #Every model in Django gets an ID column, which is the first column and kind of
            #   like our primary key.
    
    #Refresh the page so that the comment shows up after we submit it.
    comments = Comment.objects.filter(post=post_id)
    post = Post.objects.get(id=post_id)

    context = {'post':post, 'comments':comments}
    return render(request, 'FeedApp/comments.html', context)

@login_required
def friends(request):
    #Make sure the admin is the first friend request that is automatically sent out.
    #Get the admin_profile and user_profile to create the first relationship.
    admin_profile = Profile.objects.get(user = 1)
    user_profile = Profile.objects.get(user = request.user)

    #Get a list of the user's friends to display.
    user_friends = user_profile.friends.all()
    user_friends_profiles = Profile.objects.filter(user__in=user_friends)

    #Get a list of friend requests you've sent.
    user_relationships = Relationship.objects.filter(sender=user_profile)
    request_sent_profiles = user_relationships.values('receiver')

    #Get a list of who we can send a friend request to.
        #This will just be everyone except for people who are already friends,
        #   people we've already sent a friend request to, and myself.
    all_profiles = Profile.objects.exclude(user = request.user).exclude(
        id__in= user_friends_profiles).exclude(id__in = request.sent_profiles)

    #Get a list of friend requests received.
    request_received_profiles = Relationship.objects.filter(receiver=user_profile, status = 'sent')

    #Create the first relationship with the admin.
    #If this is the first time to access the friend requests page, create the first relationship
    #   with the admin of the website (so the admin is friends with everyone).

    if not user_relationships.exists():
        Relationship.objects.create(sender=user_profile, receiver=admin_profile, status = 'sent')

    #Check which submit button was pressed (sending or accepting a friend request).

    #Process the send requests.
    if request.method == 'POST' and request.POST.get("send_requests"):
        #Check to see who the receivers of the friend request(s) are
        receivers = request.POST.getlist("send_requests") #receivers is a list of profile ids
        for receiver in receivers:
            receiver_profile = Profile.objects.get(id = receiver)
            Relationship.objects.create(sender=user_profile, receiver = receiver_profile, status = 'sent')
        return redirect('FeedApp:friends')

    #Process all requests that have been received.
    if request.method == 'POST' and request.POST.get("receive_requests"):
        #Get a list of all of the senders.
        senders = request.POST.getlist("friend_requests")
        for sender in senders:
            #Update the relationship model for the sender to status 'accepted'
            Relationship.objects.filter(id = sender).update(status = 'accepted')

            #The sender needs to see that someone accepted their friend request
            #Create a relationship object to access the sender's user id to add to
            #   the friends list of the user
            relationship_obj = Relationship.objects.get(id = sender)
            user_profile.friends.add(relationship_obj.sender.user)  #Add to their friends profile

            #Add the user to the friends list of the sender's profile
            relationship_obj.sender.friends.add(request.user)

    context = {'user_friends_profiles':user_friends_profiles, 'user_relationships':user_relationships,
               'all_profiles': all_profiles, 'request_received_profiles':request_received_profiles}
    return render(request, 'FeedApp/friends.html', context)