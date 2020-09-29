# dashboard_test

- python 시각화 framework인 dash 사용하여 웹 시각화 진행 repository(https://plot.ly/dash/)

---

## 프로젝트 구조(디렉토리 단위)

- 각 스크립트 설명은 디렉토리 내 readme.md 혹은 각 스크립트 내 docstring 참조

```
dashboard_test
│
└─── README.md
│
└─── dash_tutorial (dash 공식 tutorial에서 제공하는 스크립트 모은 directory)
│   │
│   └─── 2. dash_layout
│   │
│   └─── 3. dash_callbacks
│   │
│   └─── 4. dash_state
│   │
│   └─── 5. interactive_visualizations
│   │
│   └─── map_example
│
└─── dashboard (실제 대시보드 제작 directory)
│
└─── DB_AWS_RDS (RDS의 MySQL 관련 query 포함한 directory)


```

## 스크립트 설명(세부 설명은 script 내 docstring 참고)

-  : folium 라이브러리 활용해 생활 인구 지도 시각화(모듈화 X)

- map visualization example.ipynb : folium 지도 시각화(choropleth), plotly 지도 시각화(choropleth, scattermap) 예시 코드

- make_saengwhal_visualization.py : folium 생활 인구 데이터 시각화 코드 모듈화

- saenghwal_preprocess_and_save_to_rds.py : 열린데이터 광장에서 받아오는 생활인구 데이터 전처리 후 DB에 저장


---

## 사용 데이터

- use_data 디렉토리에 생활인구 / 접근성 데이터 업로드

- 사용 데이터 정의서 링크 : https://docs.google.com/spreadsheets/d/1DySXaoGDJuRg8w3J4E2gJVDqe_FLB6ipJ6We6DlhXFE/edit#gid=0 
