# Gemini 1.5 Pro 멀티모달 프롬프트 실습

# 목표

Gemini 1.5의 멀티모달 기능을 몇가지 시나리오로 손쉽게 테스트해 봅니다.:

-   Vertex AI Generative AI 콘솔을 이용해 봅니다.
-   텍스트, 이미지, 문서, 음성, 동영상 데이터로 할 수 있는 시나리오를 살펴봅니다.
-   Cloud Run 에 대한 사용방법을 간단히 습득합니다.
-   Gemini API 를 이용해 만든 간단한 Prompt editor 툴을 이용해 좀더 대용량의 데이터로 실습을 해봅니다.
-   https://github.com/jk1333/prompt_tester

# Task 1. Vertex AI 에서 Generative AI 테스트 해보기

Google Cloud 콘솔에서 "vertex ai" 를 타이핑 하면 나오는 AI Studio 를 클릭합니다.

아래 화면과 같이 Multimodal 을 클릭하여 나오는 여러 샘플들을 하나씩 동작시켜 봅니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--51c1qrfurz5.png)

# Task 2. Vertex AI의 Gemini API 로 만든 프롬프트 앱 배포 해보기

* PROJECT_ID 정보 확보하기

Console 에 들어온 후 우측 상단의 점3개 를 클릭하여 Project settings 를 들어갑니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--zwzkr4qm90a.png)

**메모장에 Project ID 값을 기록해 둡니다.**

* IAM 수정하기

검색창에 "iam" 을 타이핑 하여 검색되는 IAM & Admin 을 들어옵니다.

Name에 Qwiklabs User Service Account 를 확인 후 우측의 연필 아이콘을 누릅니다.(Edit principal)

+ADD ANOTHER ROLE 을 누른 후 Select a role 을 클릭 후 검색창에 "Service Account User" 를 타이핑 하여 나오는걸 클릭 후 SAVE를 누릅니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/iam.png)

* YouTube Data 접근을 위한 키 생성

검색창에 "youtube data api" 를 타이핑 하여 검색되는 YouTube Data API 를 선택합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--p18qgi4z2bj.png)

ENABLE 을 누릅니다

Enable이 완료되면 우측 상단에 팝업이 뜨는 CREATE CREDENTIALS 를 누릅니다.

(혹은 검색창에서 "Credentials" 를 검색하면 나오는 APIs & Services를 들어갑니다)

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--lox1nos6o0g.png)

아래의 내용을 참고하여 키를 생성합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--pe4vjg6phca.png)

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--2pff28gct8m.png)

**나오는 키값을 별도의 메모장에 복사해 두고 DONE 을 누릅니다.**

* Vertex AI API 활성화

검색창에 "vertex ai api" 를 검색 후 Market place에서 해당 항목을 클릭, Enable 합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--uzoqxfngz5g.png)

* Multimodal 을 위한 멀티미디어 데이터 저장을 위한 Cloud Storage 생성

검색창에 "Cloud Storage" 를 검색하여 나오는 메뉴에 들어갑니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--pe79t81aa0g.png)

메뉴 상단의 CREATE 버튼을 누릅니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--0jvry2z99qci.png)

Bucket 이름에는 Global Unique 하도록 이름을 하나 지정하고 적어둡니다.

**메모장에 해당 Bucket 이름을 적어둡니다**.

Location type에는 Region 을 선택하고 asia-northeast1 (Tokyo) 를 선택합니다.

나머지는 Default 값을 두고 생성 및 Confirm 을 누릅니다.

* Prompt tester를 Cloud Run에 배포

메뉴에서 "cloud run" 을 검색합니다.

상단의 CREATE SERVICE 를 클릭합니다

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--nsoggf7s2w.png)

Container image URL에는 아래의 내용을 입력합니다.

<table>
  <thead>
    <tr>
      <th><strong>asia-northeast1-docker.pkg.dev/sandbox-373102/education/prompt_tester:v1</strong></th>
    </tr>
  </thead>
  <tbody>
  </tbody>
</table>

나머지 항목은 아래와 같이 설정합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--145e81p4nr8.png)

하단의 Container(s), Volumes, Networking, Security 를 클릭합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--72xld5gz07i.png)

**메모리는 4G를 줍니다.**

VARIABLES & SECRETS 탭에서 메모장에 기록해둔 값을 아래를 참고하여 입력합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--tmbh1rbzeh.png)

<table>
  <thead>
    <tr>
      <th>REGION</th>
      <th>asia-northeast1</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>PROJECT_ID</td>
      <td>메모장에 적어둔값</td>
    </tr>
    <tr>
      <td>BUCKET_ROOT</td>
      <td>메모장에 적어둔값</td>
    </tr>
    <tr>
      <td>YT_DATA_API_KEY</td>
      <td>메모장에 적어둔값</td>
    </tr>
    <tr>
      <td>DEFAULT_YT_VIDEO</td>
      <td><a href="https://www.youtube.com/watch?v=hMKMSRKV1Xg" target="youtube" track-type="article" track-name="youtubeLink" track-metadata-position="body">https://www.youtube.com/watch?v=hMKMSRKV1Xg</a></td>
    </tr>
  </tbody>
</table>

Security 항목으로 옮겨 Service account 항목을 Qwiklabs User Service Account 로 변경합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--owx5io8ma5a.png)

하단의 내용을 참고하여 값을 업데이트 합니다.

Request timeout 은 300 -> 3600 으로 업데이트

Execution environment 는 Default -> Second generation 으로 업데이트 합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--id68fj4t7w.png)

CREATE 를 클릭합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--vdbsyed3pvi.png)

배포가 완료되면 URL이 활성화 됩니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--yvx0jelpy2c.png)

* Prompt tester 실행

URL을 실행하고, 좌측 창에서 Text가 선택된 상태로 Add를 누릅니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--bfk8vut9dd.png)

아래와 같이 입력 후 Gemini 1.5 Flash 및 Pro 버튼을 눌러 동작을 확인합니다.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--1zo2ho4q826.png)

상단의 Samples 버튼을 클릭하여 images.zip 파일을 다운받아 둡니다.

# Task 3. 프롬프트 앱에서 시나리오 동작 해보기

**1. 스타일 분석 및 추천 (Image + Text)**

**Image:**

full_1.jpg

**Text:**

위 사진의 상의 셔츠를 바탕으로 하의에 어울리는 추천 스타일 및 피해야할 스타일을 한글로 추천해주세요

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--jcvj7lme1tm.png)

**2. 의류 선택 추천 (Image + Text + Image)**

**Image:**

pants_1.jpg, pants_2.jpg, pants_3.jpg, pants_4.jpg, pants_5.jpg

**Text:**

아래의 셔츠의 스타일을 설명하고, 위 바지들로 부터 이 셔츠와 어울리는 바지를 추천하고 추천 사유를 한글로 설명해 주세요. 그리고 비추천하는 스타일도 설명해 주세요.

**Image:**

top4.jpg

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--yp1dn5le2zl.png)

**3. PDF 문서 분석 (PDF + Text)**

**PDF(다운로드 후 앱에 업로드): **

[https://m.kisrating.com/fileDown.do?menuCd=R2&gubun=9&fileName=CI20230710-1.pdf&writedate=20230710](https://m.kisrating.com/fileDown.do?menuCd=R2&gubun=9&fileName=CI20230710-1.pdf&writedate=20230710)

**Text:**

첨부 보고서의 제목을 작성하고, 보고서의 내용을 요약해 주세요. 각 회사별로 매출 증대를 위해 추천할 내용을 알려주세요

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--dv98stxpp8i.png)

**4. 음성 요약-외국어 (Audio from YT + Text)**

**Audio from YT:**

[https://www.youtube.com/watch?v=F22D0jCGdLU](https://www.youtube.com/watch?v=F22D0jCGdLU)

**Text:**

본 음성의 내용을 시간, 화자를 포함하여 한글 자막형태로 만들어 주세요. 등장인물1, 등장인물2 와 같은 형태로 화자를 설명해 주세요

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--rl2yog6s1i.png)

**5. 비디오 요약-한국어 (Video from YT + Text)**

**Video from YT:**

[https://www.youtube.com/watch?v=hMKMSRKV1Xg](https://www.youtube.com/watch?v=hMKMSRKV1Xg)

**Text:**

첨부의 비디오를 방문 시간 및 장소 기준으로 요약해 주세요

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--fc1nasz5z3h.png)

**6. 커맨트 분석 (Comments from YT + Text)**

**Comments from YT:**

[https://www.youtube.com/watch?v=hMKMSRKV1Xg](https://www.youtube.com/watch?v=hMKMSRKV1Xg)

**Text:**

다음의 유투부 커맨트를 긍정, 부정으로 나누어 분류해 주세요. 예시로 각각 5개씩 선정해서 설명해 주세요.

![image](https://raw.githubusercontent.com/jk1333/handson/main/images/1/geminiprompt테스--3b40c2hbihj.png)