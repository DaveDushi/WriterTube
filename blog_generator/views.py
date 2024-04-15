from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
from django.conf import settings
import os
import assemblyai as aai
from openai import OpenAI
from .models import BlogPost
from dotenv import load_dotenv

load_dotenv()

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt #change this at somepoint 
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']

            # return JsonResponse({
            #     'content': yt_link
            # })
        
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({
            'error': 'invalid data sent',
        }, status=400)

        # get the yt title
        title = yt_title(yt_link)

        # check if link is in data base
        try:
            blog_already_written_by_user = BlogPost.objects.get(youtube_link=yt_link, user=request.user)
        except BlogPost.DoesNotExist:
            blog_already_written_by_user = None

        try:
            blog_already_written = BlogPost.objects.filter(youtube_link=yt_link).first()
        except BlogPost.DoesNotExist:
            blog_already_written = None

        if blog_already_written_by_user:
            return JsonResponse({
                'content': f'Article was already written for {blog_already_written_by_user.youtube_title}'
            })

        if blog_already_written:
            new_blog_article = BlogPost.objects.create(
                user=request.user,
                youtube_title=blog_already_written.youtube_title,
                youtube_link=yt_link,
                generated_content=blog_already_written.generated_content
            )
            new_blog_article.save()
            return JsonResponse({
                'content': blog_already_written.generated_content
            })

        # get transcript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({
                'error': 'Failed to get transcript'
            }, status=500)
        # use AI to genarete blog

        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({
                'error': 'Failed to generate blog aritcle'
            }, status=500)
            
        # save blog article to database
        new_blog_article = BlogPost.objects.create(
            user= request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content
        )
        new_blog_article.save()

        # return blog article as response
        return JsonResponse({'content': blog_content})

    else:
        return JsonResponse({
            'error': 'invalid request method',
        }, status=405)


def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title
 
def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = os.getenv("AAI_API_KEY") 

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text

def generate_blog_from_transcription(transcription):
    
    api_key = os.getenv("OPENAI_API_KEY") 
    client = OpenAI(api_key=api_key)
    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
            "role": "system",
            "content": "You are a professional writer."
            },
            {
            "role": "user",
            "content": "Topic/Area of Focus: Crafting a Well-Written Article Based on a YouTube Transcript\n\nInstructions/Question: Develop a polished and engaging article utilizing the content from a provided YouTube transcript. Your article should effectively convey the key points and insights from the transcript while adding context, analysis, and additional research where necessary to enhance readability and depth. \n\nCriteria for Response: Your article should demonstrate clarity, coherence, and originality. Pay attention to structure, grammar, and style to ensure the article is professional and engaging for the target audience. The article should also have proper h tags so that it can be inserted directly into html.\n\nTranscript:\nThis is a map of all of Moscow's public transportation systems. If you've never seen it before, it may look like something a three year old would draw. But it's actually extremely complex and efficient, containing the busiest metro system in the world outside of Asia, with over 2 billion annual riders every year. That's more than New York City's and Toronto's combined. To put that into perspective, each colour identifies a different line of transport and obviously there's tons of them. But first we're going to focus on these three. The Bolshaya Kozewaya line in Teal, the Moscow Central circle in red and the Koltsevaya line in brown. These three transit lines are all orbital lines, meaning they obviously go in circles. And this is extremely important for the geniusness of Moscow. See, orbital lines play a major role in major metro systems, allowing for more direct travel between different parts of the city. Without them, a purely radial system forces passengers to move inwards to the city centre to change lines and then head back outwards, making journeys longer, less efficient and also overburdening central stations. Now im not saying Moscows the only city doing this or anything, I mean Londons Circle line, Berlins Ringbahn, Tokyos Yamanote line and Shanghais line four all do the same things as well. But none of these cities have the unique multi layered system that Moscow has. The Kolsevaya line links to twelve stations that form a circle around Moscow city centre. The Moscow Central Circle or MCC for short links to 31 stations that serves greater Moscow and connects the suburbs with the city, while the Bolshaya Kulsevaya line also links 31 stations and is the outer circle easing transit lines between the outskirts of Moscow. So when you're trying to transfer between two extremely busy lines such as the Zamoskvoryskaya line and the Sokilnycheskaya line, for example, you can simply use the orbital lines to do this. But thats just one part of this. Moscows orbital lines have been meticulously planned to intersect with multiple radial lines, ensuring ease of transfer and connectivity. No other city in the world has it integrated or balanced as Moscow does. But enough with these orbital lines, because the truth is Moscow has much, much more than just this. I mean as of 2023, with all forms of public transportation combined, Moscow has 440 stations and a line length of 503 miles. But like I said, thats all forms of public transportation. And to truly appreciate Moscows transportation infrastructure, we need to break everything up. So far, everything weve mentioned makes up just some of Moscows Metro, which evidently is the bulk of Moscows infrastructure, containing 263 of the stations and 279 miles of tracks between its 15 lines, it serves not only Moscow, but also the neighbouring cities of Krasnogorsk, Ryotov, Lyubertzi and Kotalniki. As for the price of tickets through buying with the Troika card, its only 218 rubles or $2.20 for a single day ticket, which allows you to change trains as many times as you like with no limits on distance or time. For an entire month of this its literally just $20. And you dont even really need to use the card anymore because in October of 2021, the Moscow Metro became the first metro system in the world to offer face pay to their customers, meaning passengers can now pay for their ride without taking out their phone, metro or bank card, which therefore increases passenger flow at the station entrances. But heres the thing about Moscows Metro that really stands out. Its efficient. Like really efficient. The Moscow Metro is the world leader in frequency of train traffic. Intervals during peak hours dont exceed 80 seconds. Theyre the first and only country on earth to switch to the schedule. Just to understand how insane this is, NYC subway lines during peak hours have intervals of two to five minutes. The Moscow Metro also stands out in other ways too, like its beauty. While it may be the busiest metro system in Europe, it's also a tourist attraction in and of itself because of how beautifully the stations were built. See, the Moscow metro was one of the USSR's most extravagant architectural projects, with stations constructed as luxurious palaces for the people. That's how they ended up with each station being a unique work of art symbolic of Russia's pride and history. I mean, just look at both the Komsomolskaya and Maya Kowalskaya stations to see what Im talking about. Stunning. The big flaw in this metro though, is the fact they only run from 05:30 a.m. To 01:00 a.m. Leaving a four and a half hour gap of nothingness, where the only way to get around Moscow at these hours is with taxis, nine bus routes and one tram route. To be fair, this is for maintenance. But when you compare it to, say, New York City subway that runs 24 hours a day, seven days a week, you have to deduct a few points for this. But anyways, the Moscow metro is just one piece of the system. If you look back at a map of Moscows total transportation systems, I want you to now look at these lines here. Now obviously this map includes future plans till the end of 2026. So not everything on here is complete, but of these five lines, these four are complete, with this last one to be complete by 2026. Regardless, though they make up the Moscow central diameters, or MCD, for short, they stretch all across Moscow, essentially bridging the gap in between the metro and longer distance regional trains with 188 miles of lines. It's the rapid transit solution for suburban commuters, offering a direct route for these passengers without requiring them to navigate through the central metro hubs. And I mean, they're extremely important. After the first nine months of opening up, their passenger traffic was already over 100 million individual journeys. Next we have the buses. As metro stations outside the city centre are far apart in comparison to other cities, a bus network radiates from each station to the residential zones, so every major street in the city is served by at least one bus route. With an annual bus ridership of 800 million to 1 billion every year. Thats more than New York Citys and Los Angeles combined. Moscow has also been switching to electric buses. In fact, they have the second largest fleet of them in Europe, behind London, at 1050 buses. By 2030, all the buses in Moscow are planned to be fully switched over to electric too. Then theres the Moscow trams. This is a map of them. Though their importance is somewhat diminished with the rise of the metro, meaning many vital connections in the network have been withdrawn, they remain a crucial part of Moscows transportation system. Trams are still used quite a bit. Don't get me wrong, they make up 5% of all Moscow's public transportation trips, with over 600,000 people using them every single day. It's just not what it was, but they still provide important cross links between metro lines. In total, 70% of all trips made in Moscow are via public transportation, which is pretty good, higher than NYC slightly at 65% for comparison. Now, despite all of this, Moscow still has quite a few problems, most notably the traffic congestion. Despite having an incredible metro and overall transportation infrastructure, Moscow is still plagued with cars and those ten lane highways, such as the M eleven, that look straight out of an american megacity. Looking at studies online, it's consistently ranked the worst, not only in Europe but sometimes in the entire world, for traffic congestion. Keep in mind though, Moscow is the second biggest city in Europe with 13.1 million people, only behind Istanbul, and the gap isnt even that close compared to the third largest London at 9.6 million. So it is somewhat inevitable though, Moscow is working on this. Currently, in terms of car ownership, theres an average of around 300 cars per 1000 people, which honestly puts it at around the same level as London, but they are trying to lower it too, thanks to car sharing. Basically, car sharing is a model of car rental where people rent cars for short periods of time, often by the hour, and it's actually an amazing thing. See, not everyone wants a car, especially in big cities, but sometimes they're needed not every day, but usually at least once or twice a week for convenience. And that's what car sharing solves. Moscow has the biggest fleet in the world for this, with over 30,000 cars providing more than 150,000 trips every day. It's insanely cheap too, ranging from just three to 20 us cents per minute. So Moscows residents arent necessarily encouraged to get cars. If they need one, they can rent one. But it keeps car ownership lower than it could be, which is ultimately amazing for the environment and congestion overall. Moscows been working really hard to improve their public transportation. Since 2011, 187 miles of metro lines have been added to the city, along with a combined 150 metro, MCD and MCC stations, providing 3.8 million more residents with available transportation near their homes. Thats like the population of Berlin for reference. And Moscow isnt stopping here because theyre improving even more. By 2033, theres planned to be just 39 more stations opened, with their total number eventually exceeding 400, joining NYC and Shanghai as the only cities on earth past that amount. So all in all, Moscow is pretty well designed and connected in an efficient way. And while it can look chaotic sometimes from an outside perspective, like when you watch videos of their highways and traffic jams, it definitely is better than it seems. Thank you for watching.\n\nAdditional Guidance/Prompts (if applicable): Consider the target audience and purpose of the article. How can you leverage the content of the YouTube transcript to resonate with the readers and provide value? Are there any relevant supplementary materials or sources you can integrate to enrich the article?\n\nExpected Outcome: We anticipate receiving a well-crafted article that effectively utilizes the provided YouTube transcript as a foundation while adding value through insightful analysis, relevant context, and engaging writing."
            },
            {
            "role": "assistant",
            "content": "<p>When glancing at a map of Moscow's public transportation networks, one might be forgiven for thinking it resembles the doodles of a preschooler. However, beneath its seemingly simplistic facade lies a marvel of engineering and efficiency, boasting the busiest metro system outside of Asia. With over 2 billion annual riders, Moscow’s transit system outshines the likes of New York City and Toronto combined.</p>\n\n<h2>The Orbit Revolution</h2>\n\n<p>Central to Moscow's transportation brilliance are its orbital lines—Bolshaya Kozewaya line, Moscow Central Circle, and Koltsevaya line—which form a trio of interconnected circular routes. These orbital lines, a common feature in major metro systems worldwide, facilitate direct travel between different parts of the city, eliminating the need for tedious detours through the city center. This innovation not only enhances efficiency but also prevents overcrowding at central stations, making commutes smoother and faster.</p>\n\n<p>Moscow's multi-layered transport system sets it apart from other global cities. The Kolsevaya line encircles Moscow’s core, while the Moscow Central Circle links 31 stations, expanding connectivity to the city’s outskirts. The intricate design of these orbital lines enables seamless transfers between heavily trafficked routes, streamlining the commuter experience.</p>\n\n<h2>More Than Just Metro</h2>\n\n<p>While the Moscow Metro commands attention with its 263 stations and 279 miles of tracks traversing the city and its neighboring regions, the city's transportation tapestry extends beyond underground rails. The Moscow Central Diameters, spanning 188 miles, bridge the gap between metro lines and regional trains, catering to suburban commuters seeking swift and direct routes.</p>\n\n<p>Accompanying the robust metro and rail networks are Moscow's extensive bus and tram systems. A comprehensive bus network radiates from metro stations, ensuring accessibility to residential areas, while trams, though diminished in relevance, continue to serve as vital connectors between metro lines.</p>\n\n<h2>Challenges and Innovations</h2>\n\n<p>Despite its impressive infrastructure, Moscow grapples with traffic congestion, a familiar woe in major urban centers. With car ownership levels akin to London’s, the city embraces innovative solutions like car sharing to mitigate congestion and reduce environmental impact. Moscow’s transition to electric buses underscores its commitment to sustainable urban mobility, positioning it as a pioneer in eco-friendly transport initiatives.</p>\n\n<p>Looking ahead, Moscow remains steadfast in its quest for transportation excellence. Ambitious expansion plans aim to add 39 new stations by 2033, solidifying its status alongside megacities like NYC and Shanghai. As the city continues to evolve and innovate, its public transportation system stands as a testament to efficiency, connectivity, and forward-thinking urban planning.</p>\n\n<h2>Conclusion</h2>\n\n<p>While Moscow's bustling streets and highways may present a facade of chaos, exploring the intricacies of its public transportation system unveils a well-orchestrated symphony of connectivity and efficiency. From the intricately designed metro stations to the seamless integration of orbital and radial lines, Moscow’s transit network stands as a shining example of urban planning done right. As the city propels forward with its vision for a more interconnected and sustainable future, it reaffirms its status as a global leader in transportation innovation.</p>\n\n<p>Embark on a journey through Moscow's transport tapestry, where every line tells a story of efficiency, connectivity, and the relentless pursuit of excellence in urban mobility.</p>"
            },
            {
            "role": "user",
            "content": f"Topic/Area of Focus: Crafting a Well-Written Article Based on a YouTube Transcript\n\nInstructions/Question: Develop a polished and engaging article utilizing the content from a provided YouTube transcript. Your article should effectively convey the key points and insights from the transcript while adding context, analysis, and additional research where necessary to enhance readability and depth. \n\nCriteria for Response: Your article should demonstrate clarity, coherence, and originality. Pay attention to structure, grammar, and style to ensure the article is professional and engaging for the target audience. The article should also have proper h tags so that it can be inserted directly into html.\n\nTranscript:\n {transcription} \n\nAdditional Guidance/Prompts (if applicable): Consider the target audience and purpose of the article. How can you leverage the content of the YouTube transcript to resonate with the readers and provide value? Are there any relevant supplementary materials or sources you can integrate to enrich the article?\n\nExpected Outcome: We anticipate receiving a well-crafted article that effectively utilizes the provided YouTube transcript as a foundation while adding value through insightful analysis, relevant context, and engaging writing."
            },
        ],
        temperature=1,
        max_tokens=2000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
        )

    generated_content = response.choices[0].message.content.strip()


    return generated_content

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, "blog-details.html", {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})

    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeat_password = request.POST['repeatPassword']

        # check if passwords match
        if password == repeat_password:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            error_message = 'Password does not match'
            return render(request, 'signup.html', {'error_message': error_message})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')
