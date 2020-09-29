import json
import base64
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
import geopandas as gpd
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate


MAPBOX_TOKEN = 'pk.eyJ1IjoibHVja3k4MDciLCJhIjoiY2p6NzB1NzJqMG8xdzNtbWtvOXhoMXg1MyJ9.IC7MS42-BMy9MAIyZyPavA'

# 1. load and prepare data

# 1-a) 생활 인구(집계구 단위)
living_df = pd.read_csv("use_data/living_people_20190807.csv")  # 날짜 바뀌게끔 변경
# living_df.drop(['Unnamed: 0'], axis=1, inplace=True)
living_df['SMGU_CD'] = living_df['SMGU_CD'].map(str)
living_df['H_DNG_CD'] = living_df['H_DNG_CD'].map(str)

# 1-b) 생활 인구(행정동 단위)
living_df_hdong = living_df.groupby(by=['H_DNG_CD', 'TT']).sum().reset_index()

# 1-c) 집계구 단위 경계 데이터(geojson)
gibgyegu_geojson_df = gpd.read_file("use_data/서울시_집계구_2016.geojson")
gibgyegu_geojson_df.rename(columns={'TOT_OA_CD': 'SMGU_CD',
                                    'ADM_DR_CD': 'ADM_CD'}, inplace=True)
del gibgyegu_geojson_df['OBJECTID']
del gibgyegu_geojson_df['SHAPE_LENG']
del gibgyegu_geojson_df['SHAPE_AREA']

# 1-d) 행정동 단위 경계 데이터(geojson)
with open("use_data/서울_행정동_경계_2017.geojson", encoding='utf-8') as json_file:
    hdong_geojson = json.load(json_file)
    # plotly 지도 시각화 위해 id field를 추가해줘야 함
    for each in hdong_geojson['features']:
        each['id'] = each['properties']['adm_cd']

# 1-e) 자치구 단위 경계 데이터(geojson)
with open("use_data/서울_자치구_경계_2017.geojson", encoding='utf-8') as json_file:
    jachigu_geojson = json.load(json_file)

# 1-f) 행정동 코드 데이터
hdong_code = pd.read_csv('use_data/hdong_seoul_final_201804.csv')
hdong_code.dropna(inplace=True)
hdong_code['H_DNG_CD'] = hdong_code['H_DNG_CD'].map(str)
hdong_code['ADM_CD'] = hdong_code['ADM_CD'].map(str)

# 1-g) 행정동별 중심 데이터
hdong_center_df = pd.read_csv(
    "use_data/서울시_행정동_중심점_2017.csv", encoding='utf-8')

# 1-h) 자치구 중심 데이터
jachigu_center_df = pd.read_csv(
    'use_data/서울시_자치구_중심점_2017.csv', encoding='utf-8')
jachigu_center_df.drop(['Unnamed: 0'], axis=1, inplace=True)

# 1-i) 8월 한달 데이터
living_df_hdong_month = pd.read_csv(
    'use_data/month_8_living.csv', encoding='utf-8')
living_df_hdong_month['H_DNG_CD'] = living_df_hdong_month['H_DNG_CD'].map(str)
living_df_hdong_month['DATE'] = living_df_hdong_month['DATE'].map(str)
living_df_hdong_month['DATE'] = pd.to_datetime(living_df_hdong_month['DATE'])

# time-group
times = {i: str(i) for i in range(0, 24)}

# age-group
AGES = {0: "10대 미만",
        10: "10대",
        20: "20대",
        30: "30대",
        40: "40대",
        50: "50대",
        60: "60대",
        70: "70대"}

GENDER_DICT = {'female': '여자',
               'male': '남자',
               'whole': '전체'}


def make_region_dict(df: pd.DataFrame, columns: list) -> dict:
    """
    key가 더 큰 단위, value가 각 key에 속한 작은 단위의 지역을 담은 dictionary 생성
    ex) {'강남구' : ['A동', 'B동', 'C동'], '강서구': ['D동', 'E동', 'F동']}

    :param df: 행정동 코드 dataframe
    :param columns: ["SIDO_NM", "SIGUNGU_NM"] or ["SIGUNGU_NM", "DNG_NM"] 두 조합만 가능
    """
    result = {}
    parent_list = list(df[columns[0]].unique())
    parent_list.sort()

    for each in parent_list:
        children_list = list(df[df[columns[0]] == each][columns[1]].unique())
        children_list.sort()
        result[each] = children_list

    return result


def make_column_by_gender_age(gender, age):

    result = ""

    if gender == 'male':
        result += 'M'
    elif gender == "female":
        result += 'F'
    else:  # 전체
        return 'SPOP'

    if age < 10:
        result += '00'
    else:
        result += str((age // 10) * 10)

    return result


def make_word_using_gender_age(gender, age):

    result = ""
    if gender == 'whole':
        return "전체"
    else:
        result += GENDER_DICT[gender] + " " + AGES[(age//10)*10]

    return result


sido_sigungu_dict = make_region_dict(
    df=hdong_code, columns=['SIDO_NM', 'SIGUNGU_NM'])  # key : 시도 , value : 시도별 자치구
sigungu_hdong_dict = make_region_dict(
    df=hdong_code, columns=['SIGUNGU_NM', 'DNG_NM'])  # key : 자치구, value : 자치구별 행정동

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']  # css


app = dash.Dash(__name__, external_stylesheets=external_stylesheets,)

# app 설정
app.title = '개원상권 분석 보고서'
app.scripts.config.serve_locally = False
app.css.config.serve_locally = True
app.config.suppress_callback_exceptions = True

# app.scripts.append_script({
#     'external_url': 'r'
# })

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# 메인창 레이아웃
index_page = html.Div([

    html.Div([  # 제목 +로고 창

        html.H4("개원상권 분석 시스템 Beta Ver."),
        html.Img(src='/assets/startdoctor.png', id="logo")

    ], className="header"),

    html.Hr(id="header-bottom-line"),

    html.Div([

        html.Div([  # 생활 인구 설명
            html.H3("생활 인구란?"),
            html.B("사람이 직접 거리에서 측정하는 기존의"),
            html.Pre(" "),
            html.P(" 유동인구보다 "),
            html.Pre(" "),
            html.B("더 정확한 개념!"),

            html.Br(),
            html.P("공공 빅데이터와 통신 데이터를 이용해"),
            html.Br(),
            html.P("그 지역, 그 시간대에 존재하는"),
            html.Pre(" "),
            html.B("진짜 인구수"),
            html.Pre(" "),
            html.P("를 알려드립니다."),

            html.H3("내게 맞는 개원 지역, 궁금하지 않으신가요?"),
            html.P("스타트닥터의 개원상권분석시스템 베타 버전은"),
            html.Br(),
            html.P("의료계에 특화된 빅데이터를 다각도로 분석한 인구-환자분석 시스템입니다."),
            html.Br(),
            html.P("내게 맞는 개원 지역,"),
            html.Pre(" "),
            html.B("Step을 따라, 직접 분석해보세요!")

        ], className="explain-living-area"),

        html.Div([  # 지역 선택 + 성별 / 연령 선택
            html.H2("Step 1"),
            html.P("궁금하신"),
            html.Pre(" "),
            html.B("지역"),
            html.P("을 선택해 결과를 확인해보세요"),
            html.Div([  # 지역 선택
                dcc.Dropdown(id='si-select',
                             options=[
                                 {'label': '서울특별시', 'value': '서울특별시'}
                             ],
                             value='서울특별시',
                             disabled=True
                             ),
                dcc.Dropdown(id='gu-select',
                             value="강남구"),
                dcc.Dropdown(id="hdong-select",
                             value="역삼1동"),

            ], className="select-area"),

            html.H2("Step 2", id="step2"),
            html.B("성별"),
            html.P("과"),
            html.Pre(" "),
            html.B("연령"),
            html.P("을 자유롭게 선택해보세요"),
            html.Br(),
            html.P("*전체를 선택하신 경우엔 연령대 설정이 불가능합니다."),
            html.Br(),

            html.Div([  # 성별 / 연령 선택
                dcc.RadioItems(  # select gender
                    id='gender-select',
                    options=[
                        {'label': "남자", 'value': 'male'},
                        {'label': "여자", 'value': 'female'},
                        {'label': "전체", 'value': 'whole'},
                    ],
                    value='male',
                    labelStyle={'display': 'inline-block'},
                ),
                dcc.Slider(  # select age
                    id='age-select',
                    min=min(AGES.keys()),
                    max=max(AGES.keys()),
                    value=30,
                    marks=AGES,
                    disabled=False
                )],
                className='select-gender-age'),
        ], className='select-area-gender-age'),

        html.Div([
            dcc.Graph('living-choropleth'),
            dcc.Slider(
                id='time-select',
                min=0,
                max=23,
                value=12,
                marks=times,
            )
        ], className="map-area"),
        html.H2("Step 3"),
        html.P("지도의 하단에 있는 시간 설정 도구를 활용하여", id="s3P"),
        html.Br(),
        html.B("내 병원에 맞는 운영전략", id="s3b"),
        html.P("을 세워보세요.", id="s3p2"),
        html.Br(),
        html.Br(),
        html.H2("Step 4", id="final")
    ], className="temp"),

    html.Div([

        html.Div([  # 동 이름, 시간, 생활 인구 수
                    html.H5(id="text-hdong"),
                    html.Div(id="text-time"),
                    html.Div(id='text-num-living-people'),
                    html.Div(id="hdong-living-score-day")
        ], className="hdong-result-living-area"),

        html.Div([
            dcc.Graph("hdong-time-series-plot-Oneday-gender-age"),
            dcc.Graph("hdong-time-population-composition")
        ], className="graph-area")

    ], className="result-area"),

    html.Button([
        dcc.Link([
            html.Img(src="/assets/more.png")
        ], href="/accessibility")
    ], className="next-btn"),

    html.Div([
        html.Div([
            html.P("STARTDOCTOR")
        ], className='inner1'),
        html.Div([
            html.P("Tel : 050-7348-2605", id="tel"),
            html.P("E-mail : support@eszett.co.kr", id="email"),
            html.P("상호 : 에스체트(eszett)", id='sangho'),
            html.P("사업자등록번호 : 308-13-51102")
        ], className='inner2'),
    ], className='footer'),

])

# 경쟁 분석 링크 레이아웃
page_1_layout = html.Div([

    html.Div([
        html.Div([
            html.A([
                html.Img(src="/assets/alarm_survey.png"),
            ], href="http://startdoc.co.kr/46")
        ], id='survey'),

        html.Div([
            html.A([
                html.Img(src="/assets/register.png"),
                ], href="http://startdoc.co.kr/42")
            ], id='register'),

        ], className='wrapper')

    ], id='eszett')

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):

    if pathname == '/accessibility':
        return page_1_layout
    else:
        return index_page

# callback functions
@app.callback(
    Output('gu-select', 'options'),
    [Input('si-select', 'value')]
)
def set_jachigu_options(selected_si):

    return [{'label': each, 'value': each} for each in sido_sigungu_dict[selected_si]]


@app.callback(
    Output('hdong-select', 'options'),
    [Input('gu-select', 'value')]
)
def set_hdong_options(selected_gu):

    if selected_gu is None:
        raise PreventUpdate

    return [{'label': each, 'value': each} for each in sigungu_hdong_dict[selected_gu]]


@app.callback(
    [Output('text-hdong', 'children'),
     Output('text-time', 'children'),
     Output("text-num-living-people", 'children')],
    [Input("si-select", 'value'),
     Input('gu-select', 'value'),
     Input("hdong-select", 'value'),
     Input("time-select", 'value'),
     Input("gender-select", 'value'),
     Input("age-select", 'value'),
     ]
)
def update_hdong_time_num_living_people(gu, si, hdong, time, gender, age):

    if hdong is None:
        raise PreventUpdate
    date = '2019-09-10 5일 전의 최신 생활 인구데이터를 사용합니다.'

    gender_age = make_column_by_gender_age(gender, age)
    word = make_word_using_gender_age(gender, age)

    h_code = hdong_code[hdong_code['DNG_NM'] == hdong]['H_DNG_CD'].iloc[0]
    df = living_df_hdong[(living_df_hdong['TT'] == time)
                         & (living_df_hdong['H_DNG_CD'] == h_code)]

    living_num = int(df[gender_age].iloc[0])

    return "{} {} {}".format(si, gu, hdong), date, "{} 생활인구 수 : {} 명".format(word, living_num)


@app.callback(
    Output('age-select', 'disabled'),
    [Input('gender-select', 'value')]
)
def age_disabled_if_gender_is_whole(gender):
    if gender == 'whole':
        return True
    return False


@app.callback(
    Output('hdong-living-score-day', 'children'),
    [Input("hdong-select", 'value'),
     Input("time-select", 'value'),
     Input('gender-select', 'value'),
     Input('age-select', 'value')]
)
def update_living_score(hdong, time, gender, age):

    gender_age = make_column_by_gender_age(gender, age)

    if hdong is None:
        raise PreventUpdate

    h_code = hdong_code[hdong_code['DNG_NM'] == hdong]['H_DNG_CD'].iloc[0]
    df = living_df_hdong[living_df_hdong['TT'] == time]
    df['hdong_rank'] = df[gender_age].rank(ascending=True)

    max_val = df['hdong_rank'].max()
    min_val = df['hdong_rank'].min()

    df['hdong_score'] = df['hdong_rank'].map(
        lambda rank: round(((rank - min_val) / max_val) * 10, 1))

    score = df[df['H_DNG_CD'] == h_code].iloc[0]['hdong_score']

    word = make_word_using_gender_age(gender, age)

    return "{} 환자 유입력 : {}점 / 10".format(word, score)


@app.callback(
    [Output('gu-select', 'value'),
     Output('hdong-select', 'value')],
    [Input('living-choropleth', 'clickData')
     ])
def update_gu_hdong_dropdown_by_click_map(clickData):

    if clickData is None:
        raise PreventUpdate

    click_hdong = clickData['points'][0]['text']
    # click_gu =  ""

    for gu, hdongs in sigungu_hdong_dict.items():
        if click_hdong in hdongs:
            click_gu = gu
            return click_gu, click_hdong

    # return None, None


@app.callback(
    Output('living-choropleth', 'figure'),
    [Input('gu-select', 'value'),
     Input('hdong-select', 'value'),
     Input('time-select', 'value'),
     Input('gender-select', 'value'),
     Input('age-select', 'value'),
     ])
def update_living_choropleth(selected_gu, selected_hdong, selected_time, selected_gender, selected_age):

    filtered_df = living_df_hdong[living_df_hdong['TT'] == selected_time]
    final_df = pd.merge(left=filtered_df, right=hdong_code, on='H_DNG_CD')

    gender_age = make_column_by_gender_age(selected_gender, selected_age)
    max_living_hdong = living_df_hdong[gender_age].max()
    min_living_hdong = living_df_hdong[gender_age].min()

    seoul_center = (37.5642135, 127.0016985)

    if selected_gu is None:  # 서울 전체의 시각화

        return {
            'data': [go.Choroplethmapbox(
                locations=final_df['ADM_CD'],
                z=final_df[gender_age],
                zmin=min_living_hdong,
                zmax=max_living_hdong,
                geojson=hdong_geojson,
                colorscale='YlOrRd',
                marker={"opacity": 0.5},
                text=final_df['DNG_NM'],
                # hovertext=final_df[gender_age].map(lambda x: str(int(x)) + "명"),
                hoverinfo="text+z",
                colorbar=dict(title='생활인구 수(명)', tickformat=",")

            )],
            'layout': go.Layout(
                margin={'l': 5, 'b': 5, 't': 5, 'r': 5},
                # yaxis=dict(tickformat="%"),
                # width='100%,
                height=380,
                # title={'text' : '서울특별시 생활인구'},
                mapbox_style="open-street-map",
                mapbox_zoom=10,
                mapbox_center={"lat": float(
                    seoul_center[0]), "lon": float(seoul_center[1])},
                clickmode='event',

            )
        }

    elif selected_hdong is None:  # 특정 구의 동 단위 시각화

        final_df_gu = final_df[final_df['SIGUNGU_NM'] == selected_gu]
        jachigu_center = jachigu_center_df[jachigu_center_df['SIGUNGU_NM'] == selected_gu]

        return {
            'data': [go.Choroplethmapbox(
                locations=final_df_gu['ADM_CD'],
                z=final_df_gu[gender_age],
                geojson=hdong_geojson,
                colorscale='YlOrRd',
                marker={"opacity": 0.5},
                text=final_df_gu['DNG_NM'],
                hoverinfo="text+z",
                colorbar=dict(title='생활인구 수(명)', tickformat=",")
            )],
            'layout': go.Layout(
                margin={'l': 30, 'b': 5, 't': 5, 'r': 5},
                # title={'text' : '{} 생활인구'.format(selected_gu)},
                height=380,
                mapbox_style="open-street-map",

                mapbox_zoom=12,
                mapbox_center={"lat": float(
                    jachigu_center['Y']), "lon": float(jachigu_center['X'])},
                clickmode='event',

            )}

    else:  # 특정 동의 집계구 단위 시각화
        h_code = hdong_code[hdong_code['DNG_NM']
                            == selected_hdong]['H_DNG_CD'].iloc[0]
        h_code_adm = hdong_code[hdong_code['DNG_NM']
                                == selected_hdong]['ADM_CD'].iloc[0]
        hdong_center = hdong_center_df[hdong_center_df['DNG_NM']
                                       == selected_hdong]

        df = living_df[(living_df['H_DNG_CD'] == h_code) &
                       (living_df['TT'] == selected_time)]
        geo_df = gibgyegu_geojson_df[gibgyegu_geojson_df['ADM_CD'] == h_code_adm]
        final_df = pd.merge(left=geo_df, right=df, on='SMGU_CD')
        final_geojson = json.loads(final_df.to_json())

        for each in final_geojson['features']:
            each['id'] = each['properties']['SMGU_CD']

        return {
            'data': [go.Choroplethmapbox(
                     locations=final_df['SMGU_CD'],
                     z=final_df[gender_age],
                     geojson=final_geojson,
                     colorscale='YlOrRd',
                     marker={"opacity": 0.5},
                     text=final_df['SMGU_CD'],
                     hoverinfo="z",
                     colorbar=dict(title='생활인구 수(명)', tickformat=",")
                     )],
            'layout': go.Layout(
                margin={'l': 5, 'b': 5, 't': 5, 'r': 5},
                # title={'text': '{}의 집계구별 생활인구'.format(selected_hdong)},
                # width=650,
                height=380,
                mapbox_style="open-street-map",
                mapbox_zoom=13,
                mapbox_center={"lat": float(
                             hdong_center['Y']), "lon": float(hdong_center['X'])},
                clickmode="none"
            )
        }


@app.callback(
    Output("hdong-time-series-plot-Oneday-gender-age", 'figure'),
    [Input('hdong-select', 'value'),
     Input('gender-select', 'value'),
     Input('age-select', 'value')
     ])
def update_time_series_hdong(hdong, gender, age):

    gender_age = make_column_by_gender_age(gender, age)
    word = make_word_using_gender_age(gender, age)

    if hdong is None:
        raise PreventUpdate

    h_code = hdong_code[hdong_code['DNG_NM'] == hdong]['H_DNG_CD'].iloc[0]
    # 특정 행정동
    df = living_df_hdong[living_df_hdong['H_DNG_CD'] == h_code]

    return {
        'data': [go.Scatter(
            x=df['TT'],
            y=df[gender_age],
            name=hdong,
        )],
        'layout': go.Layout(
            margin={'l': 65, 'b': 45, 't': 45, 'r': 45},
            xaxis={'title': '시간(hour)'},
            yaxis={'title': '생활인구 수(명)', 'tickformat': ","},
            title={'text': "{} {} 하루 생활인구 수 변화".format(hdong, word),
                   'x': 0},
            font=dict(size=11),
            # width=650,
            height=280

        )
    }


@app.callback(
    Output("hdong-time-population-composition", "figure"),
    [Input('hdong-select', 'value'),
     Input('time-select', 'value')
     ])
def update_horziontal_barplot_show_people_ratio(hdong, time):

    if hdong is None:
        raise PreventUpdate

    h_code = hdong_code[hdong_code['DNG_NM'] == hdong]['H_DNG_CD'].iloc[0]
    df = living_df_hdong[(living_df_hdong['H_DNG_CD'] == h_code) & (
        living_df_hdong['TT'] == time)]

    x = list(df.iloc[0][3:])  # 각 성별, 세대별 생활 인구 수
    y = ['남 10대 미만', '남 10대', '남 20대', '남 30대', '남 40대', '남 50대', '남 60대', '남 70대 이상',
         '여 10대 미만', '여 10대', '여 20대', '여 30대', '여 40대', '여 50대', '여 60대', '여 70대 이상']

    colors = ['#397A98'] * 8 + ['#E45569'] * 8

    return {
        'data': [
            go.Bar(
                x=x,
                y=y,
                orientation='h',
                marker_color=colors
            )
        ],
        'layout': go.Layout(
            margin={'l': 55, 'b': 45, 't': 45, 'r': 45},
            xaxis={'title': '생활인구 수(명)', 'tickformat': ","},
            # yaxis={'title': '연령대'},
            title={'text': "{}의 {}시 성별, 연령별 인구 수".format(hdong, time),
                   'x': 0},
            font=dict(size=11),
            # width=650,
            height=280
        ),
    }


if __name__ == '__main__':

    app.run_server(host="0.0.0.0", debug=False, port=8080)