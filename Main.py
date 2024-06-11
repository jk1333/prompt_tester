import streamlit as st
import os
from pytube import YouTube
from pytube.exceptions import VideoUnavailable
from vertexai.preview.generative_models import grounding
from vertexai.generative_models import Part, Tool
from datetime import datetime

REGION = os.environ['REGION']
PROJECT_ID = os.environ['PROJECT_ID']
BUCKET_ROOT = os.environ['BUCKET_ROOT']
YT_DATA_API_KEY = os.environ['YT_DATA_API_KEY']
DEFAULT_YT_VIDEO = os.environ['DEFAULT_YT_VIDEO']

GENERATIVE_MODEL_V1_5_PRO = "gemini-1.5-pro-001"
GENERATIVE_MODEL_V1_5_FLASH = "gemini-1.5-flash-001"

if 'containers' not in st.session_state:
    st.session_state['containers'] = []
    st.session_state['result'] = None

st.set_page_config(layout='wide')

@st.cache_resource
def get_bucket():
    from google.cloud import storage
    storage_client = storage.Client()
    return storage_client.bucket(BUCKET_ROOT)

tool_google_search = Tool.from_google_search_retrieval(grounding.GoogleSearchRetrieval())

from collections import defaultdict
import pandas as pd
import googleapiclient.discovery
def get_video_comments(video_id, max_comments = 30):
    # the following is grabbing channel videos
    # counting number of videos grabbed
    import html
    n_comments = 0
    next_page_token = None
    comments_dic = defaultdict(list)
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey = YT_DATA_API_KEY)
    class MAX(Exception): pass
    try:
        while True:
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': 100
            }
            if next_page_token:
                params['pageToken'] = next_page_token
            res = youtube.commentThreads().list(**params).execute()
            
            comments = res.get("items")
            for comment in comments:
                n_comments += 1
                comment = comment["snippet"]["topLevelComment"]["snippet"]
                comments_dic["text"].append(html.escape(comment["textDisplay"]).replace(",", " "))
                comments_dic["author"].append(comment["authorDisplayName"])
                comments_dic["likes"].append(comment["likeCount"])
                comments_dic["published"].append(comment["publishedAt"])
                comments_dic["updated"].append(comment["updatedAt"])
                if n_comments == max_comments:
                    raise MAX
            if "nextPageToken" in res:
                next_page_token = res["nextPageToken"]
            else:
                break
    except MAX:
        pass
    except Exception as e:
        print(e)
        return pd.DataFrame()
    return pd.DataFrame(comments_dic)

def count_tokens(contents, model_name):
    from vertexai.generative_models import GenerativeModel
    def get_model():
        return GenerativeModel(model_name)
    response = get_model().count_tokens(contents)
    return response.total_tokens, response.total_billable_characters

def analyze_gemini(contents, model_name, instruction, response_mime, token_limit, bUse_Grounding):
    from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
    def get_model():
        return GenerativeModel(model_name)
        #return GenerativeModel(model_name, system_instruction=instruction)
    generation_config={
        "candidate_count": 1,
        "max_output_tokens": token_limit,
        "temperature": 0,
        "top_p": 0.5,
        "top_k": 1
    }
    if response_mime != 'text/plain':
        generation_config['response_mime_type'] = response_mime
    responses = get_model().generate_content(
        contents=contents,
        generation_config=generation_config,
        safety_settings={
            HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        },
        stream=True, 
        tools=[tool_google_search] if bUse_Grounding else None
    )

    return responses
    #return responses.text, responses.to_dict()['usage_metadata']

def download_audio(video):
    file = f"{video.video_id}.mp3"
    if os.path.exists(file) == False:
        video.streams.get_audio_only().download(".", filename=file)
    blob = get_bucket().blob(file)
    if blob.exists() == False:
        blob.upload_from_filename(file)

def download_video(video):
    file = f"{video.video_id}.mp4"
    if os.path.exists(file) == False:
        video.streams.get_highest_resolution().download(".", filename=file)
    blob = get_bucket().blob(file)
    if blob.exists() == False:
        blob.upload_from_filename(file)

def upload_multimedia(filename, filetype, size, raw):
    blob = get_bucket().blob(f"uploads/{filename}")
    if (blob.exists() == False) or (blob.size != size):
        blob.upload_from_string(data=raw, content_type=filetype)

def text_block(idx, text):
    st.caption("Text block")
    text = st.text_area("Text", text, key=f"block-Text-{idx}", label_visibility="collapsed")
    if (text == None) or (text == ""):
        text = " "
    return [text]

def image_block(idx):
    st.caption("Image block")
    images = []
    cols = st.columns([2, 3])
    uploaded_files = cols[0].file_uploader("Images to add", ['png', 'jpg'], key=f"block-Image-Uploader-{idx}", accept_multiple_files=True, label_visibility="collapsed")
    for uploaded_file in uploaded_files:
        cols[1].image(uploaded_file.getvalue(), "Source", use_column_width=True)
        images.append(Part.from_data(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
    return images

def multimedia_block(idx):
    st.caption("Multimedia block (Max 32MB per file on Cloud Run)")
    uploaded_file = st.file_uploader("Multimedia to add", ['mp3', 'wav', 'flac', 'mp4', 'wmv', 'mov', 'webm'], key=f"block-Multimedia-Uploader-{idx}", accept_multiple_files=False, label_visibility="collapsed")
    if uploaded_file == None:
        return [""]
    if uploaded_file.type.startswith("video/"):
        st.video(uploaded_file.getvalue(), format=uploaded_file.type, loop=True)
    elif uploaded_file.type.startswith("audio/"):
        st.audio(uploaded_file.getvalue(), format=uploaded_file.type)
    upload_multimedia(uploaded_file.name, uploaded_file.type, uploaded_file.size, uploaded_file.getvalue())
    return [Part.from_uri(uri=f"gs://{BUCKET_ROOT}/uploads/{uploaded_file.name}", mime_type=uploaded_file.type)]

def pdf_block(idx):
    st.caption("PDF block (Max 32MB per file on Cloud Run)")
    pdfs = []
    uploaded_files = st.file_uploader("PDFs to add", ['pdf'], key=f"block-PDF-Uploader-{idx}", accept_multiple_files=True, label_visibility="collapsed")
    for uploaded_file in uploaded_files:
        pdfs.append(Part.from_data(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
    return pdfs

def yt_video_block(idx, URL):
    st.caption("YouTube Video block")
    video_url = st.text_input("YouTube Video URL", URL, key=f"block-Text-YTVideo-{idx}")
    if (video_url == None) or (len(video_url) == 0):
        return [""]
    video = YouTube(video_url)
    try:
        video.check_availability()
    except VideoUnavailable:
        st.error("Video is unavailable")
        return [""]
    st.video(video.watch_url)
    with st.spinner("Downloading video..."):
        download_video(video)
    st.success("Video Ready")
    return [Part.from_uri(uri=f"gs://{BUCKET_ROOT}/{video.video_id}.mp4", mime_type="video/mp4")]

def yt_audio_block(idx, URL):
    st.caption("YouTube Audio block")
    cols = st.columns([2, 1])
    video_url = cols[0].text_input("YouTube Video URL", URL, key=f"block-Text-YTAudio-{idx}")
    if (video_url == None) or (len(video_url) == 0):
        return [""]
    video = YouTube(video_url)
    try:
        video.check_availability()
    except VideoUnavailable:
        st.error("Video is unavailable")
        return [""]
    with st.spinner("Downloading audio..."):
        download_audio(video)
    cols[1].success("Audio Ready")
    st.audio(f"{video.video_id}.mp3", format="audio/mp3")
    return [Part.from_uri(uri=f"gs://{BUCKET_ROOT}/{video.video_id}.mp3", mime_type="audio/mp3")]

def yt_comments_block(idx, URL):
    st.caption("Comments from YouTube")
    video_url = st.text_input("YouTube Video URL", URL, key=f"block-Text-YTComments-{idx}")
    if (video_url == None) or (len(video_url) == 0):
        return [""]
    if st.button(f"Delete", key=f"block-Text-YTComments-Button-{idx}"):
        st.session_state['containers'].pop(idx)
        st.rerun()
    video = YouTube(video_url)
    try:
        video.check_availability()
    except VideoUnavailable:
        st.error("Video is unavailable")
        return ""
    comments_df = get_video_comments(video.video_id)
    st.dataframe(comments_df, use_container_width=True, height=200)
    comments = ""
    for comment in comments_df['text'].tolist():
        comments += "* " + comment + "\n"
    text = st.text_area("Text", comments, key=f"block-Text-YTAudio-STT-{idx}", label_visibility="collapsed")
    return [text]

def create_input_container(idx, container_type, default_value):
    result = None
    container = st.container(border=2)
    with container:
        match container_type:
            case "Text":
                result = text_block(idx, default_value)
            case "Image":
                result = image_block(idx)
            case "PDF":
                result = pdf_block(idx)
            case "Multimedia":
                result = multimedia_block(idx)
            case "Video from YouTube":
                if default_value == None:
                    default_value = DEFAULT_YT_VIDEO
                result = yt_video_block(idx, default_value)
            case "Audio from YouTube":
                if default_value == None:
                    default_value = DEFAULT_YT_VIDEO
                result = yt_audio_block(idx, default_value)
            case "Comments from YouTube":
                if default_value == None:
                    default_value = DEFAULT_YT_VIDEO
                result = yt_comments_block(idx, default_value)
    return result

def create_button_set(idx):
    prompt = None
    with st.container(border=1):
        st.caption("Add prompt block")
        col_left, col_right = st.columns([3, 1])
        option = col_left.selectbox("Add prompt block", 
                              ("Text", "Image", "PDF", "Multimedia", 
                               "Audio from YouTube", "Video from YouTube", "Comments from YouTube"), 
                               label_visibility="collapsed", key=f"select-Prompt-{idx}")
        if col_right.button("Add", key=f"btn-Add-{idx}", use_container_width=True):
            prompt = option
    return prompt

#with st.sidebar:
#    expander = st.expander("History")
#    if expander.button("Clear history", type="primary", use_container_width=True):
#        del st.session_state["history"]
#        st.session_state["history"] = []
#    for idx, history in reversed(list(enumerate(st.session_state[HISTORY_KEY]))):
#        if expander.button(f'{idx+1}.{history["request"]}', use_container_width=True):
#            st.session_state[SESSION_KEY]["request"] = history["request"]
#            st.session_state[SESSION_KEY]["response"] = history["response"]
#            st.experimental_rerun()
@st.cache_data
def get_file(filename):
    data = None
    with open(filename, "rb") as file:
        data = file.read()
    return data

def gemini_stream_out(responses):
    for response in responses:
        try:
            yield response.text
        except Exception as e:
            yield response.to_dict()
    yield response.usage_metadata

col_left, col_right = st.columns([1, 2])

CONTENTS = []

with col_left:
    container_type = create_button_set(-1)
    if container_type != None:
        st.session_state['containers'].insert(0, (container_type, None))
    for idx, (container_type, default_value) in enumerate(st.session_state['containers']):
        result = create_input_container(idx, container_type, default_value)
        CONTENTS += result
        container_type = create_button_set(idx)
        if container_type != None:
            st.session_state['containers'].insert(idx+1, (container_type, None))

with col_right:
    with st.container(border=1):
        if len(CONTENTS) > 0:
            tokens, billable = count_tokens(CONTENTS, GENERATIVE_MODEL_V1_5_PRO)
            st.caption(f"Total tokens: {tokens}, Billable characters: {billable}")
        instruction = None
        #instruction = st.text_input("System instruction (Only for Gemini 1.5 and 1.0 Text)", "Answer as concisely as possible and give answer in Korean")
        cols = st.columns(5)
        response_option = cols[0].selectbox("Response option", ('text/plain', 'application/json'), label_visibility="collapsed")
        max_tokens = cols[1].text_input("Token limit", 8192, label_visibility="collapsed")
        bUse_Grounding = cols[2].checkbox("Google\nGrounding")
        cols[3].download_button("Samples", data=get_file('images.zip'), file_name="images.zip", use_container_width=True)
        if cols[4].button("Clear cache", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
        cols = st.columns(2)
        model_name = None
        if cols[0].button("Gemini 1.5 Flash", use_container_width=True):
            model_name = GENERATIVE_MODEL_V1_5_FLASH
        if cols[1].button("Gemini 1.5 Pro", use_container_width=True):
            model_name = GENERATIVE_MODEL_V1_5_PRO
    if model_name != None:
        result_container = st.container()
        with st.spinner(f"Analyzing {len(CONTENTS)} items using {model_name}"):
            now = datetime.now()
            responses = analyze_gemini(CONTENTS, model_name, instruction, response_option, int(max_tokens), bUse_Grounding)
            with st.container(border=1):
                text = st.write_stream(gemini_stream_out(responses))
            st.session_state['result'] = {}
            st.session_state['result']['elapsed'] = (datetime.now() - now).seconds
            st.session_state['result']['text'] = text
        result_container.success(f"Took {st.session_state['result']['elapsed']} seconds")
    else:
        if st.session_state['result'] != None:
            with st.container(border=1):
                st.write(st.session_state['result']['text'])