import streamlit as st
from google import genai
from google.genai import types
import time
from google.cloud import aiplatform
import os

BUCKET_ROOT = os.environ['BUCKET_ROOT']
YT_DATA_API_KEY = os.environ['YT_DATA_API_KEY']
DEFAULT_YT_VIDEO = os.environ['DEFAULT_YT_VIDEO']

PROJECT_ID = aiplatform.initializer.global_config.project
DEFAULT_REGION = aiplatform.initializer.global_config.location

MODELS = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash-001", "gemini-2.0-flash-lite-001"]
MEDIA_RESOLUTION = [None, "MEDIA_RESOLUTION_UNSPECIFIED", "MEDIA_RESOLUTION_LOW", "MEDIA_RESOLUTION_MEDIUM", "MEDIA_RESOLUTION_HIGH"]

COUNTRIES = ['KR', 'US', 'DE', 'FR', 'GB', 'JP']
INTERESTS = {
    'All':'0', 'Film & Animation':'1', 'Autos & Vehicles':'2', 'Music':'10', 'Pets & Animals':'15',
    'Sports':'17', 'Gaming':'20', 'People & Blogs':'22', 'Entertainment':'24', 'News & Politics':'25',
    'Howto & Style':'26', 'Science & Technology':'28'
    }

if 'containers' not in st.session_state:
    st.session_state['containers'] = []
    st.session_state['result'] = None

st.set_page_config(layout='wide', page_icon="✨")

@st.cache_resource
def get_bucket():
    from google.cloud import storage
    storage_client = storage.Client()
    return storage_client.bucket(BUCKET_ROOT)

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

def get_most_popular(country_code, category_id = "0", max_videos = 50):
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey = YT_DATA_API_KEY)
    response = youtube.videos().list(part="snippet,statistics", chart="mostPopular", 
                                     regionCode=country_code, maxResults=max_videos, videoCategoryId=category_id).execute()
    videos = response["items"]
    playlist = ""
    for video in videos:
        playlist += f"* 'Channel title': '{video['snippet']['title']}', 'Content title': '{video['snippet']['channelTitle']}'\n"
    return playlist

def count_tokens(contents, model_name, region, media_resolution):
    client = genai.Client(vertexai=True, location=region, project=PROJECT_ID)    
    response = client.models.count_tokens(model=model_name, contents=contents,
                                          config=types.CountTokensConfig(
                                              generation_config=types.GenerateContentConfig(
                                                  media_resolution=media_resolution
                                              )
                                          ))
    return response.total_tokens, response.cached_content_token_count

def get_default_model_config(model_name):
    if model_name.startswith("gemini-2.5"):
        include_thoughts=True
        region = "us-west1"
        token_limit = 65535
        budget = "auto"
    else:
        include_thoughts = None
        region = "us-west1"
        token_limit = 8192
        budget = 0
    return {"thoughts": include_thoughts, "region": region, "token_limit": token_limit, "budget": budget}

def analyze_gemini(contents, model_name, region, instruction, response_mime, token_limit, bUse_Grounding, budget = "auto", media_resolution = None):
    def get_client():
        return genai.Client(vertexai=True, location=region, project=PROJECT_ID)

    tools = [types.Tool(google_search=types.GoogleSearch())]

    if model_name.startswith("gemini-2.5-pro"):
        thinking_config = types.ThinkingConfig(include_thoughts=True if budget != "0" else False)
    elif model_name.startswith("gemini-2.5-flash"):
        thinking_config = types.ThinkingConfig(include_thoughts=True if budget != "0" else False,
                                               thinking_budget=None if budget in ["auto", "0"] else int(budget))
    else:
        thinking_config = None

    generate_content_config = types.GenerateContentConfig(
        temperature = 1,
        top_p = 0.95,
        max_output_tokens = token_limit,
        response_modalities = ["TEXT"],
        safety_settings = [types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="OFF"
            )
        ],
        tools = tools if bUse_Grounding else None,
        thinking_config = thinking_config,
        media_resolution = media_resolution,
        system_instruction = instruction
    )

    if response_mime != 'text/plain':
        generate_content_config.response_mime_type = response_mime

    responses = get_client().models.generate_content_stream(
        model = model_name,
        contents=contents,
        config = generate_content_config
    )

    return responses
    #return responses.text, responses.to_dict()["usage_metadata"]

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
        cols[1].image(uploaded_file.getvalue(), "Source", use_container_width=True)
        images.append(types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
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
    return [types.Part.from_uri(file_uri=f"gs://{BUCKET_ROOT}/uploads/{uploaded_file.name}", mime_type=uploaded_file.type)]

def multimedia_uri_block(idx):
    st.caption("Multimedia uri block")
    contents_url = st.text_input("Public URL or Google Cloud Storage URL", key=f"block-Multimedia-URI-{idx}")
    mime_type = st.text_input("Mimetype (ex: video/mp4)", key=f"block-Multimedia-URI-Mimetype-{idx}")
    return [types.Part.from_uri(file_uri=contents_url, mime_type=mime_type)]

def pdf_block(idx):
    st.caption("PDF block (Max 32MB per file on Cloud Run)")
    pdfs = []
    uploaded_files = st.file_uploader("PDFs to add", ['pdf'], key=f"block-PDF-Uploader-{idx}", accept_multiple_files=True, label_visibility="collapsed")
    for uploaded_file in uploaded_files:
        pdfs.append(types.Part.from_bytes(data=uploaded_file.getvalue(), mime_type=uploaded_file.type))
    return pdfs

def yt_video_block(idx, URL):
    st.caption("YouTube Video block")
    video_url = st.text_input("YouTube Video URL", URL, key=f"block-Text-YTVideo-{idx}")
    if (video_url == None) or (len(video_url) == 0):
        return [""]
    st.video(video_url)
    return [types.Part.from_uri(file_uri=video_url, mime_type="video/mp4")]

def yt_comments_block(idx, URL):
    st.caption("Comments from YouTube")
    video_url = st.text_input("YouTube Video URL", URL, key=f"block-Text-YTComments-{idx}")

    comments_df = get_video_comments(video_url[video_url.rfind("v=")+2:])
    st.dataframe(comments_df, use_container_width=True, height=200)
    comments = ""
    for comment in comments_df['text'].tolist():
        comments += "* " + comment + "\n"
    text = st.text_area("Text", comments, key=f"block-Text-YTComments-Result-{idx}", label_visibility="collapsed")
    return [text]

def yt_trends_block(idx):
    st.caption("Trends from YouTube")
    cols = st.columns(2)
    country = cols[0].selectbox("Countries", COUNTRIES)
    interests = cols[1].selectbox("Global interests", INTERESTS.keys())
    playlist = get_most_popular(country, INTERESTS[interests])
    text = st.text_area("Text", playlist, key=f"block-Text-YTTrends-Result-{idx}", label_visibility="collapsed")
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
            case "Multimedia URL":
                result = multimedia_uri_block(idx)
            case "Video from YouTube":
                if default_value == None:
                    default_value = DEFAULT_YT_VIDEO
                result = yt_video_block(idx, default_value)
            case "Comments from YouTube":
                if default_value == None:
                    default_value = DEFAULT_YT_VIDEO
                result = yt_comments_block(idx, default_value)
            case "Trends from YouTube":
                result = yt_trends_block(idx)
    return result

def create_button_set(idx):
    prompt = None
    with st.container(border=1):
        st.caption("Add prompt block")
        col_left, col_right = st.columns([3, 1])
        option = col_left.selectbox("Add prompt block", 
                              ("Text", "Image", "PDF", "Multimedia", "Multimedia URL",
                               "Video from YouTube", "Comments from YouTube", "Trends from YouTube"), 
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

metadata = None
def gemini_stream_out(responses):
    thinking = False
    for response in responses:
        for part in response.candidates[0].content.parts:
            if part and part.thought:
                if thinking == False:
                    yield "Thinking steps\n\n"
                    yield "---\n"
                    thinking = True
                yield part.text
            else:
                if thinking == True:
                    thinking = False
                    yield "---\n"
                yield response.text
    global metadata
    metadata = (response.usage_metadata, 
                response.candidates[0].grounding_metadata, 
                response.candidates[0].citation_metadata)

col_left, col_right = st.columns([1, 2])

CONTENTS = []

with col_left:
    instruction = st.text_area("System instruction")
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
        cols = st.columns([2, 1, 1, 1])
        model = cols[0].selectbox("Model", MODELS)
        config = get_default_model_config(model)
        budget = cols[1].text_input("Thinking budget", config["budget"], disabled=config["budget"] == 0)
        region = cols[2].text_input("Region", config["region"])
        cols[3].download_button("Download\nSamples", data=get_file('images.zip'), file_name="images.zip", use_container_width=True)
        #instruction = st.text_input("System instruction (Only for Gemini 1.5 and 1.0 Text)", "Answer as concisely as possible and give answer in Korean")
        cols = st.columns(5)
        media_resolution = cols[0].selectbox("Media resolution", MEDIA_RESOLUTION, label_visibility="collapsed")
        response_option = cols[1].selectbox("Response option", ('text/plain', 'application/json', 'text/x.enum'), label_visibility="collapsed")
        max_tokens = cols[2].text_input("Token limit", config["token_limit"], label_visibility="collapsed")
        bUse_Grounding = cols[3].checkbox("Google\nGrounding")
        
        aiplatform.init(location=region)
    if len(CONTENTS) > 0:
        tokens, cached_tokens = count_tokens(CONTENTS, model, region, media_resolution)
        st.caption(f"Total tokens: {tokens}, Cached tokens: {cached_tokens}")
    if cols[4].button("Execute", use_container_width=True):
        result_container = st.container()
        with st.spinner(f"Analyzing {len(CONTENTS)} items using {model}"):
            start_time = time.time()
            responses = analyze_gemini(CONTENTS, model, region, instruction if len(instruction) > 0 else None, response_option, int(max_tokens), bUse_Grounding, budget, media_resolution)
            with st.container(border=1):
                text = st.write_stream(gemini_stream_out(responses))
                elapsed_time = time.time() - start_time
                st.json(metadata[0])
                if metadata[1]:
                    grounding_metadata = metadata[1]
                    if grounding_metadata.search_entry_point:
                        st.markdown(grounding_metadata.search_entry_point.rendered_content, unsafe_allow_html=True)
                    if grounding_metadata.grounding_supports:
                        for supports in grounding_metadata.grounding_supports:
                            with st.container(border=1):
                                st.markdown(f"{supports.grounding_chunk_indices} {supports.segment.text} [{supports.segment.start_index}:{supports.segment.end_index}] ({supports.confidence_scores})", unsafe_allow_html=True)
                        for idx, chunk in enumerate(grounding_metadata.grounding_chunks):
                            st.link_button(f"[{idx}] 🌏 {chunk.web.title}", chunk.web.uri)
                if metadata[2]:
                    st.json(metadata[2])
            st.session_state['result'] = {}
            st.session_state['result']['elapsed'] = f"{elapsed_time:.2f}"
            st.session_state['result']['text'] = text
        result_container.success(f"Took {st.session_state['result']['elapsed']} seconds")
    else:
        if st.session_state['result'] != None:
            with st.container(border=1):
                st.write(st.session_state['result']['text'])