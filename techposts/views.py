import requests
from bs4 import BeautifulSoup
from django.shortcuts import render
from .models import AllPosts
from operator import itemgetter
import json
import datetime as d
from .forms import PostForm
from .models import AllContents
from techposts.utils import search_func # this function does the model query heavy lifting for modelsearch_view    
from django.views.generic.list import ListView
###################################################
# Home (Index page)
################################################### 
def home(request):
    """ Shows a menu of views for the user to try """
    return render(request, 'techposts/index') 
 
 
###################################################
# ERRORS: puts up a generic error page. Maybe I have to turn off debug to see this? I don't know.
###################################################
def errors_view(request):
    return (render(request, 'rechposts/error_page')) 

####################################################
# This view uses the blogger API to get all the posts and stores them in the db
###################################################
def get_and_store_view(request):
  '''
  Uses the blogger API and the requests module to get all the posts, and stores one post per record in the database   
  '''
  AllPosts.objects.all().delete()  # clear the table
  newstring = " " # newstring lets us put out something to the screen
  counter = 0
  for blogid in ['4018409536126807518', '8358870650052717118', '3338358600077930557', '3984132750383546180']:
    
    def request_by_year(edate, sdate):
        # Initially I did the entire request at once, but I had to chunk it into years because it was timing out in windows.
     
        
        # Speaking Python: 
        url = "https://www.googleapis.com/blogger/v3/blogs/" + \
        blogid + \
        "/posts?endDate=" + edate + "&fetchBodies=false&maxResults=500&startDate=" + \
            sdate + \
            "&status=live&view=READER&fields=items(title%2Curl)&key=AIzaSyDleLQNXOzdCSTGhu5p6CPyBm92we3balg"
        r = requests.get(url, stream=True)
        q = json.loads(r.text)  # this is the better way to unstring it
        if not q:
            s = []
        else:
            s = q['items']
        return (s)

    accum_list = []  # this will become a list of dictionaries
    c_year = int(d.datetime.now().year)

    for the_year in range(2014, c_year + 1):
        enddate = str(the_year) + "-12-31T00%3A00%3A00-00%3A00"
        startdate = str(the_year) + "-01-01T00%3A00%3A00-00%3A00"
        t = request_by_year(enddate, startdate)
        accum_list = accum_list + t

    #sorteditems = sorted(accum_list, key=itemgetter('title'), reverse=True)
    sorteditems = sorted(accum_list, key=itemgetter('title'))
    sorteditems.reverse()
 
  
    # Now we get ready to update the database
    
    for mylink in sorteditems:
         
        counter += 1
        newstring = "<a href=" + mylink['url'] + ">" + \
            mylink['title'] + "</a>" + "<br>" + newstring
            # Below, notice I stuff the title in with the body. It makes the title search part of the contents search.
        newrec = AllPosts.objects.create(
            anchortext=mylink['title'],
            hyperlink="<a href=" + mylink['url'] + ">" + mylink['title'] + "</a>" + "<br>",
            url=mylink['url']
        )
        newrec.save()

  return render(request, 'techposts/get-and-store', {'allofit': newstring, 'count': counter})   
############################################# 
def scrapecontents_view(request):
    '''
    Scrape the contents of every post
    Here's the psuedocode:
    1. X Go into the AllPosts model
    2. X Retrieve all the hyperlinks and put them in a list
    3. X Loop through the hyperlinks
        a. X Get post and find everything inside post-body, eliminate all html
        b. X Store all contents in the new model AllContents.Fullpost    
        c. X Also update AllCOntents.Hyperlink        
    4. X Put something out to the template 
 
    '''
    # First, get all the urls from AllPosts
    instance = AllPosts.objects.filter().values_list('url', 'anchortext')
    from django.db import IntegrityError
    # I'm starting over each time, by emptying out AllContents
    AllContents.objects.all().delete()  # clear the table 
    for hyper, title in instance: 
         
        getpost = requests.get(hyper)
        soup = BeautifulSoup(getpost.text, 'html.parser')            
        soup_contents = soup.find("div", class_="post-body entry-content") 
        stripped = title + soup_contents.get_text()
        stripped=stripped.replace('\n',' ') # need to replace newline with a blank
        stripped = ' '.join(stripped.split()) # remove all multiple blanks, leave single blanks      
        try: 
            newrec = AllContents.objects.create(
                fullpost=stripped,       
                hyperlink=hyper,
                title=title
            )
        except IntegrityError:
            return render(request, 'techposts/error_page')    
        newrec.save()   
    return render(request, 'techposts/scrapecontents')


############# 
def modelsearch_view(request):
    '''  
    This is the view that searches the model, also known as the database, also called the search index.
    I query using values_list(). The alternative would have been values() which creates a nice dictionary,
    which should be easier because I can see the keywords, but whatever. So instead I am referring to the indices:
    [0] # search terms
    [1] # url
    [2] # title    
    [-1] # the number of search terms found per post
    ''' 
    
    form = PostForm(request.POST)       
    if request.method == 'POST': # this means the user has filled out the form     
        try:           
            user_terms=""   
            form.data = form.data.copy()  # Make a mutable copy
            if form.data['user_search_terms'][-1] == ",": # Ditch any trailing commas          
           
                form.data['user_search_terms'] = form.data['user_search_terms'][:-1]
                
                while True:
                    if form.data['user_search_terms'][-1] == ",":
                        form.data['user_search_terms'] = form.data['user_search_terms'][:-1]
                    else:
                        break    
                 
            # Now I also have to handle any duplicate commas           
            user_string_parts = form.data['user_search_terms'].split(',') 
            user_string_parts = [part.strip() for part in user_string_parts ]
            #while("" in user_string_parts) :  # THis while loop doesn't look necessary
            #    user_string_parts.remove("")                
            form.data['user_search_terms'] = (', '.join(user_string_parts) )   


            # Next, run it thorugh modelform validation, then call my search_func to do all the query heavy lifting
            if form.is_valid():    
                cd = form.cleaned_data  # Clean the user input
                user_terms = cd['user_search_terms']  # See forms.py
                user_terms = [each_string.lower() for each_string in user_terms] # I like them to all be lowercase               
                context = search_func(user_terms) # The function does all the query heavy lifting                               
                context.update({'form': form}) 
            
            else:    
                context = {'form': form}       
            return render(request, 'techposts/modelsearch', context)    
        except IndexError:
            context = {'form': form}         
    else: # This code executes the first time this view is run. It shows an empty form to the user  
        context = {'form': form}     
    return render(request, 'techposts/modelsearch', context)

#################################################################################
# CLASS BASED VIEW Now retrieve the postss using a class-based view (ListView) 
#################################################################################
class ModelList(ListView): # ListView doesn't have a template

    model = AllPosts  # This tells Django which model to create listview for
    # I left all the defaults.
    # The default name of the queryset is object_list. It can be changed like this: context_object_name='all_model_recipes' 
    # The default template becomes allrecipes_list.html   