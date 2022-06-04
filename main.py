# Importing the libraries we will need throughout the project.

from googleapiclient.discovery import build
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import emoji
import streamlit as st
import matplotlib.ticker as ticker


# For using YouTube Data API we need a personal API key and then a list of channels id that we want to analyze.

api_key = 'AIzaSyCcSuI7ZewyOnuD5pcwvR05-Z1srMRREaU'
channel_ids = ['UCyG7zAV_2JlPnxhwDxZN6sA', 'UC6NrrEp1e3-A51SSinM3Y-Q', 'UCQG_fzADCunBTV1KwjkfAQQ', 'UCrFlv9c4LItVlIMCC2p6LOg', 'UCFiYPUhUzLKoi-cZ0AwpjLA', 'UCC8bTxyN2ZCfMzS_JAEClfA', 'UCg_xrQ9KMN7wL4moBwuxZWw', 'UCvsp8e2LrbUAuE5oLHrBQ_Q', 'UCf8zNN8N7U2BEm4WBQnWBIw', 'UCSD0MKMFT0bZP4jj6c5ihMw', 'UCrRn4Vat9iyUGtl6jPjG3IA', 'UC_RDtmUq7RISJ4mFKAhjzTg', 'UCStb6xqP228XXUykrrY-_CQ', 'UCA9n787LX5srHH-KTv_yZ9Q', 'UCrailkufB1aKrKc6l1osRgw', 'UCiiV8stcewhoCNyiErr7GtA']
youtube = build('youtube', 'v3', developerKey = api_key)


# function to get general statistics about the channels. 

def get_channel_stats(youtube, channel_id):
    
    request = youtube.channels().list(part ='snippet, contentDetails, statistics', id = channel_id)
    response = request.execute()
    data = dict(Channel_name= response['items'][0]['snippet']['title'],
                   Subscribers_Count= response['items'][0]['statistics']['subscriberCount'],
                   Total_Views_Count= response['items'][0]['statistics']['viewCount'],
                    Total_Videos= response['items'][0]['statistics']['videoCount'],
                    DateStarted= response['items'][0]['snippet']['publishedAt'],
                    playlist_id =response['items'][0]['contentDetails']['relatedPlaylists']['uploads'] )
    return data


# Let's put all general statistics in one dataframe.

general_stats = pd.DataFrame()

for i in range(len(channel_ids)):
    data = pd.Series(get_channel_stats(youtube, channel_ids[i])).to_frame().T
    general_stats = pd.concat([general_stats, data], axis=0)

general_stats = general_stats.reset_index(drop=True)


# function to get all video ids of a channel.

def get_video_ids(youtube, playlist_id):
    request = youtube.playlistItems().list(part = 'contentDetails',playlistId = playlist_id, maxResults=100)
    response = request.execute()
    videos_id = []
    for i in range(len(response['items'])):
        videos_id.append(response['items'][i]['contentDetails']['videoId'])
    
    next_page_token = response.get('nextPageToken')
    more_pages = True
    
    while more_pages:
        if next_page_token is None:
            more_pages = False
        else:
            request = youtube.playlistItems().list(part = 'contentDetails',playlistId = playlist_id, maxResults=100, pageToken = next_page_token)
            response = request.execute()
            for i in range(len(response['items'])):
                videos_id.append(response['items'][i]['contentDetails']['videoId'])
            
            next_page_token = response.get('nextPageToken')
            
        
    return videos_id


# Let's store all video ids, it will be a list of lists that contain video ids for each channel seperately.

video_ids = []

for i in range(len(channel_ids)):
    video_ids.append(get_video_ids(youtube, general_stats.playlist_id.iloc[i]))


# function to get video details

def get_video_details(youtube, video_ids):
    all_video_stats = []
    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(part = 'snippet, statistics', id=','.join(video_ids[i:i+50])) # limit to requests is 50 
        response = request.execute()
        
        for video in response['items']:
            video_stats = dict(Title = video['snippet']['title'], Publish_Date =video['snippet']['publishedAt'],
                                        Views = video['statistics']['viewCount'], Likes= video['statistics'].get('likeCount',0),
                                         Comments = video['statistics'].get('commentCount', 0))
            all_video_stats.append(video_stats)
            
            
    return all_video_stats


# Storing all video information dataframes in a list.

video_dfs = []

for i in range(len(channel_ids)):
    df = pd.DataFrame(get_video_details(youtube, video_ids[i]))
    df['Identity'] = general_stats.Channel_name.iloc[i]  # to know to which channel the video belongs.
    video_dfs.append(df)


# Concating all video_dfs dataframes into one big dataframe.

video_df = pd.DataFrame()

for df in video_dfs:
    video_df = pd.concat([video_df, df], axis=0)

video_df= video_df.reset_index(drop=True)


# Let's change the type of the numeric columns to int, and the date column to date, instead of object.

general_stats['Subscribers_Count'] = pd.to_numeric(general_stats['Subscribers_Count'])
general_stats['Total_Views_Count'] = pd.to_numeric(general_stats['Total_Views_Count'])
general_stats['Total_Videos'] = pd.to_numeric(general_stats['Total_Videos'])
general_stats['DateStarted'] = pd.to_datetime(general_stats['DateStarted']).dt.date.astype('datetime64')


video_df['Views'] = pd.to_numeric(video_df['Views'])
video_df['Likes'] = pd.to_numeric(video_df['Likes'])
video_df['Comments'] = pd.to_numeric(video_df['Comments'])
video_df['Publish_Date'] = pd.to_datetime(video_df['Publish_Date']).dt.date.astype('datetime64')


# Function to remove emojis from video titles.

def remove_emoji(text):
    return emoji.replace_emoji(text, replace='')


# Let's remove the emojies from the titles since its gonna interfere with the plots.

video_df.Title  = video_df.Title.apply(remove_emoji)

fprop = fm.FontProperties(fname='NotoSansCJKtc-Regular.otf') # a font that supports Korean, Chinese and Japanese characters.


###############################################################################################
##################################### Support Functions #######################################
###############################################################################################



# Function to return top 10 viewed videos ever.

def top_10_viewed(df):
    fig, ax = plt.subplots()
    plt.ticklabel_format(style='plain', axis='y')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{:,.0f}'.format(x/1000000) + 'M'))
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ordered = df.sort_values('Views', ascending=False)
    top_10 = ordered.head(10)
    plt.xticks(rotation=90)
    sns.barplot(y=top_10['Views'] , x=top_10['Title'], palette ='Blues_r').set_xticklabels(labels = top_10['Title'],fontproperties=fprop, fontsize=12);
    for bar, label in zip(ax.patches, top_10['Identity']):
        x = bar.get_x()
        width = bar.get_width()
        height = bar.get_height()
        ax.text(x+width/2., height + 0.2, label, ha="center", fontproperties=fprop, fontsize=3.5) 



# Function to return top 10 viewed videos for a specific channel.

def top_10_viewed_by_name(df, name):
    fig, ax = plt.subplots()
    ax.ticklabel_format(useOffset=False, style='plain')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{:,.0f}'.format(x/1000000) + 'M'))

    name_df = df[df.Identity == name]
    ordered = name_df.sort_values('Views', ascending=False)
    top_10 = ordered.head(10)
    plt.xticks(rotation=90)
    sns.barplot(y=top_10['Views'] , x=top_10['Title'], palette ='Blues_r').set_xticklabels(labels = top_10['Title'],fontproperties=fprop, fontsize=12);


# TOP 10 Liked videos ever.

def top_10_Liked(df):
    fig, ax = plt.subplots()
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{:,.0f}'.format(x/1000) + 'K'))
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ordered = df.sort_values('Likes', ascending=False)
    top_10 = ordered.head(10)
    plt.xticks(rotation=90)
    sns.barplot(y=top_10['Likes'] , x=top_10['Title'], palette ='Blues_r').set_xticklabels(labels = top_10['Title'],fontproperties=fprop, fontsize=12);
    for bar, label in zip(ax.patches, top_10['Identity']):
        x = bar.get_x()
        width = bar.get_width()
        height = bar.get_height()
        ax.text(x+width/2., height + 0.2, label, ha="center", fontproperties=fprop, fontsize=3.5) 



# Top 10 Liked Videos by Channel.

def top_10_Liked_by_name(df, name):
    fig, ax = plt.subplots()
    ax.ticklabel_format(useOffset=False, style='plain')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: '{:,.0f}'.format(x/1000) + 'K'))
    name_df = df[df.Identity == name]
    ordered = name_df.sort_values('Likes', ascending=False)
    top_10 = ordered.head(10)
    plt.xticks(rotation=90)
    sns.barplot(y=top_10['Likes'] , x=top_10['Title'], palette ='Blues_r').set_xticklabels(labels = top_10['Title'],fontproperties=fprop, fontsize=12);


# Count of subscribers for each channel.

def sub_count(df):
    fig, ax = plt.subplots()
    ax.ticklabel_format(useOffset=False, style='plain')
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.get_xaxis().set_visible(False)
    names = general_stats['Channel_name']
    subs = general_stats['Subscribers_Count']
    names_ordered = general_stats.sort_values('Subscribers_Count', ascending=False).Channel_name
    sns.barplot(x=subs, y=names, palette='Blues_r', order=names_ordered).set_yticklabels(labels=names_ordered,fontproperties=fprop,fontsize=12);
    ax.bar_label(ax.containers[0], fmt = '%d');


# Line plot of dates the channels got started.

def timeline(df):
    fig, ax = plt.subplots();
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    plt.xticks(rotation=90);

    names = general_stats['Channel_name']
    ordered = general_stats.sort_values('DateStarted', ascending=True)

    sns.lineplot(x=ordered['Channel_name'], y=ordered['DateStarted'], palette='Blues', marker="o").set_xticklabels(labels = ordered['Channel_name'],fontproperties=fprop, fontsize=12);



###############################################################################################
##################################### STREAMLIT PART ##########################################
###############################################################################################


st.set_option('deprecation.showPyplotGlobalUse', False)
st.set_page_config(layout="wide")


sidebar_list = general_stats.Channel_name.tolist()
sidebar_list.insert(0, "General Stats")

side_bar = st.sidebar.selectbox('Which channel would you like to check ?', sidebar_list)


if side_bar == "General Stats":

    st.markdown("<h1 style='text-align: center; color: #8CC0DE;'>YouTube Channel Analysis</h1>", unsafe_allow_html=True)
    st.write("")
    st.write("")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        col1.header("Total Channels")
        col1.write(str(len(general_stats)))

    with col2:
        col2.header("Total Nr. Videos")
        col2.write(str(general_stats.Total_Videos.sum()))

    with col3:
        col3.header("Min Nr. Subs")
        col3.write(str(general_stats.Subscribers_Count.min()))

    with col4:
        col4.header("Max Nr. Subs")
        col4.write(str(general_stats.Subscribers_Count.max()))


    st.write("")
    st.write("")


    st.write(' #### Subscribers Count ***By Channel*** : ')
    st.pyplot(sub_count(video_df))

    st.write("")

    st.write(' #### ***Timeline*** of Channels creation date : ')
    st.pyplot(timeline(video_df))

    st.write("")

    st.write(' #### Top 10 ***Viewed***  Videos : ')
    st.pyplot(top_10_viewed(video_df))

    st.write("")

    st.write(' #### Top 10 ***Liked***  Videos : ')
    st.pyplot(top_10_Liked(video_df))



def st_page(name):

    st.write(f""" # {name} Channel Analysis """)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        col1.header("Subs Count")
        col1.write(str(int(general_stats.Subscribers_Count[general_stats.Channel_name == name])))

    with col2:
        col2.header("Total Videos")
        col2.write(str(len(video_df[video_df.Identity == name])))

    with col3:
        col3.header("Total Views")
        col3.write(str(int(general_stats.Total_Views_Count[general_stats.Channel_name == name])))

    with col4:
        col4.header("Date Started")
        col4.write(str(general_stats[general_stats.Channel_name == name]['DateStarted'].astype('datetime64[s]').item().strftime('%Y.%m.%d')))
    

    st.write("")
    st.write("")

    st.write(' ### Top 10 viewed videos for this channel: ')
    st.pyplot(top_10_viewed_by_name(video_df, name))

    st.write("")

    st.write(' ### Top 10 liked videos for this channel: ')
    st.pyplot(top_10_Liked_by_name(video_df, name))



if side_bar == '지현꿍':
    st_page('지현꿍')

if side_bar == 'Nebom 사계절의 네봄':
    st_page('Nebom 사계절의 네봄')

if side_bar == '滇西小哥 Dianxi Xiaoge':
    st_page('滇西小哥 Dianxi Xiaoge')

if side_bar == 'deemd 딤디':
    st_page('deemd 딤디')

if side_bar == '매일맛나 delicious day':
    st_page('매일맛나 delicious day')

if side_bar == '쿠킹하루 Cooking Haru :)':
    st_page('쿠킹하루 Cooking Haru :)')

if side_bar == '꿀주부 Honeyjubu':
    st_page('꿀주부 Honeyjubu')

if side_bar == '효뎡 Dyeong':
    st_page('효뎡 Dyeong')

if side_bar == '野小妹wild girl':
    st_page('野小妹wild girl')

if side_bar == '세리티 Serity':
    st_page('세리티 Serity')

if side_bar == '로하Roha':
    st_page('로하Roha')

if side_bar == 'Namiのくらし':
    st_page('Namiのくらし')

if side_bar == '우리의식탁 W TABLE':
    st_page('우리의식탁 W TABLE')

if side_bar == '闽湖阿嬤Fujian Grandma':
    st_page('闽湖阿嬤Fujian Grandma')

if side_bar == '냥숲nyangsoop':
    st_page('냥숲nyangsoop')

if side_bar == '야미보이 Yummyboy':
    st_page('야미보이 Yummyboy')
