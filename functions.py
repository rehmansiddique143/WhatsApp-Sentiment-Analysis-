import re
from collections import Counter
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd
import seaborn as sns
import streamlit as st
from collections import Counter
import matplotlib.pyplot as plt
import urlextract
import emoji
from wordcloud import WordCloud


def generateDataFrame(file):
    data = file.read().decode("utf-8")
    data = data.replace('\u202f', ' ')
    data = data.replace('\n', ' ')
    pattern = '\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s?(?:AM\s|PM\s|am\s|pm\s)?-\s'
    msgs = re.split(pattern, data)[1:]
    date_times = re.findall(pattern, data)
    date = []
    time = []
    for dt in date_times:
        date.append(re.search('\d{1,2}/\d{1,2}/\d{2,4}', dt).group())
        time.append(re.search('\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?', dt).group())
#separate users and messsages 
    users = []
    message = [] 
    for m in msgs:
        entry = re.split('([\w\W]+?):\s', m)
        if (len(entry) < 3):
            users.append("Notifications")
            message.append(entry[0])
        else:
            users.append(entry[1])
            message.append(entry[2])
    df = pd.DataFrame(list(zip(date, time, users, message)), columns=["Date", "Time(U)", "User", "Message"])
    return df
# ok 
# Find user 
def getUsers(df):
    users = df['User'].unique().tolist()
    users.sort()
    users.remove('Notifications')
    users.insert(0, 'Everyone')
    return users
# Extarct Links and Media file
def getStats(df):
    media = df[df['Message'] == "<Media omitted> "]
    media_cnt = media.shape[0]
    df.drop(media.index, inplace=True)
    deleted_msgs = df[df['Message'] == "This message was deleted "]
    deleted_msgs_cnt = deleted_msgs.shape[0]
    df.drop(deleted_msgs.index, inplace=True)
    temp = df[df['User'] == 'Notifications']
    df.drop(temp.index, inplace=True)
     
    extractor = urlextract.URLExtract()
     
    links = []
    for msg in df['Message']:
        x = extractor.find_urls(msg)
        if x:
            links.extend(x)
    links_cnt = len(links)
    word_list = []
    for msg in df['Message']:
        word_list.extend(msg.split())
    word_count = len(word_list)
    msg_count = df.shape[0]
    return df, media_cnt, deleted_msgs_cnt, links_cnt, word_count, msg_count
# Extarct Emojis
def getEmoji(df):
    emojis = []
    for message in df['Message']:
        emojis.extend([c for c in message if c in emoji.EMOJI_DATA])
    return pd.DataFrame(Counter(emojis).most_common(len(Counter(emojis))))

#Preprocessing
def PreProcess(df,dayf):
    #per  day
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=dayf)
    #per time
    df['Time'] = pd.to_datetime(df['Time(U)']).dt.time
    #per year
    df['year'] = df['Date'].apply(lambda x: int(str(x)[:4]))
    # per month
    df['month'] = df['Date'].apply(lambda x: int(str(x)[5:7]))
    df['date'] = df['Date'].apply(lambda x: int(str(x)[8:10]))
    df['day'] = df['Date'].apply(lambda x: x.day_name())
    df['hour'] = df['Time'].apply(lambda x: int(str(x)[:2]))
    df['month_name'] = df['Date'].apply(lambda x: x.month_name())
    return df


def getMonthlyTimeline(df):

    df.columns = df.columns.str.strip()
    df=df.reset_index()
    timeline = df.groupby(['year', 'month']).count()['Message'].reset_index()
    time = []
    for i in range(timeline.shape[0]):
        time.append(str(timeline['month'][i]) + "-" + str(timeline['year'][i]))
    timeline['time'] = time
    return timeline


def MostCommonWords(df):
    f = open('stop_hinglish.txt')
    stop_words = f.read()
    f.close()
    words = []
    for message in df['Message']:
        for word in message.lower().split():
            if word not in stop_words:
                words.append(word)
    return pd.DataFrame(Counter(words).most_common(20))

def dailytimeline(df):
    df['taarek'] = df['Date']
    daily_timeline = df.groupby('taarek').count()['Message'].reset_index()
    fig, ax = plt.subplots()
    #ax.figure(figsize=(100, 80))
    ax.plot(daily_timeline['taarek'], daily_timeline['Message'])
    ax.set_ylabel("Messages Sent")
    st.title('Daily Timeline')
    st.pyplot(fig)

def WeekAct(df):
    x = df['day'].value_counts()
    fig, ax = plt.subplots()
    ax.bar(x.index, x.values)
    ax.set_xlabel("Days")
    ax.set_ylabel("Message Sent")
    plt.xticks(rotation='vertical')
    st.pyplot(fig)

def MonthAct(df):
    x = df['month_name'].value_counts()
    fig, ax = plt.subplots()
    ax.bar(x.index, x.values)
    ax.set_xlabel("Months")
    ax.set_ylabel("Message Sent")
    plt.xticks(rotation='vertical')
    st.pyplot(fig)

def activity_heatmap(df):
    period = []
    for hour in df[['day', 'hour']]['hour']:
        if hour == 23:
            period.append(str(hour) + "-" + str('00'))
        elif hour == 0:
            period.append(str('00') + "-" + str(hour + 1))
        else:
            period.append(str(hour) + "-" + str(hour + 1))

    df['period'] = period
    user_heatmap = df.pivot_table(index='day', columns='period', values='Message', aggfunc='count').fillna(0)
    return user_heatmap
def create_wordcloud(df):

    f = open('stop_hinglish.txt', 'r')
    stop_words = f.read()
    f.close()
    def remove_stop_words(message):
        y = []
        for word in message.lower().split():
            if word not in stop_words:
                y.append(word)
        return " ".join(y)

    wc = WordCloud(width=500,height=500,min_font_size=10,background_color='white')
    df['Message'] = df['Message'].apply(remove_stop_words)
    df_wc = wc.generate(df['Message'].str.cat(sep=" "))
    return df_wc
#Get Sentiment Analysis
def get_sentiment(df):
    df['Date']=pd.to_datetime(df['Date'])
    data=df.dropna()
    sentiments=SentimentIntensityAnalyzer()
    data["positive"]=[sentiments.polarity_scores(i)["pos"] for i in df["Message"]]
    data["negative"]=[sentiments.polarity_scores(i)["neg"] for i in df["Message"]]
    data["neutral"]=[sentiments.polarity_scores(i)["neu"] for i in df["Message"]]
    # data["positive"]=abs( data["positive"]) 
    x=sum(data["positive"])
    y=sum(data["negative"])
    z=sum(data["neutral"])
    sizes = [x,y,z]
    labels = ['Positive chat','Negative chat', 'Neutral chat']
    fig1, ax1 = plt.subplots()
    ax1.pie(sizes ,labels=labels, autopct='%1.1f%%')
    st.pyplot(fig1)
     
    


# df['sentiment'] = df['message'].apply(get_sentiment)



# def sentiment_analysis(df):
#     pos,neu,neg=0,0,0
#     for line in df['Message']:
#         chat=line.split('-')[1].split(':')[1]
#         analysis=TextBlob(chat)
#         val=analysis.sentiment.polarity
#         if val>0:
#             pos+=val
#         elif val==0:
#             neu+=1
#         else:
#             neg+=val
#             print(pos,neu,neg)
#     neg=abs(neg)
#     labels = ['positive chat','negative chat']
#     sizes = [pos,neg]
#     fig1, ax1 = plt.subplots()
#     ax1.pie(sizes ,labels=labels, autopct='%1.1f%%')
#     plt.title('Whatsapp Sentiment Analysis')
#     return plt.show()