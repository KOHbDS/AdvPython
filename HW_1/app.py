import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import datetime
from sklearn.linear_model import LinearRegression


month_to_season = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn"}

def season_now():
    now = datetime.datetime.now().month
    return month_to_season[now]

def trends_by_season(df):
    trend_res = {}
    for season in df.season.unique():
        _df = df[df.season == season]
        _df['year'] = pd.DatetimeIndex(_df['timestamp']).year.tolist()
        _df = _df.groupby('year').temperature.mean().reset_index()
        X = _df.year.to_numpy().reshape(-1, 1)
        y = _df.temperature.to_numpy()
        trend = LinearRegression().fit(X, y).coef_[0]
        trend_res.update({season: 'up' if trend > 0 else 'down'})
    return trend_res

def process_temperature_data_v2(data):
    results = {}
    cities = data['city'].unique()
    for city in cities:
        city_data = data[data['city'] == city]
        city_data['rolling_mean'] = city_data['temperature'].rolling(window=30).mean()
        city_data['rolling_std'] = city_data['temperature'].rolling(window=30).std()
        mean_temp = city_data['temperature'].mean()
        std_temp = city_data['temperature'].std()
        results.update({
            city: {
            'average': mean_temp,
            'min': city_data['temperature'].min(),
            'max': city_data['temperature'].max(),
            'season_avg': city_data.groupby('season')['temperature'].mean().to_dict(),
            'season_std': city_data.groupby('season')['temperature'].std().to_dict(),
            'trend': trends_by_season(city_data),
        }})
    return results

st.title("HW1 Прикладной Python")
st.write("**Анализ температурных данных и мониторинг текущей температуры через OpenWeatherMap API**")

st.subheader('* Загрузка данных для температурных данных (CSV)')
uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    data['timestamp'] = pd.to_datetime(data.timestamp)
    st.dataframe(data.groupby('season')['temperature'].agg(average='mean', std='std').reset_index())
    
    st.write(f'Уникальных городов {data.city.nunique()}')
    st.write(data.city.unique().tolist())
    
    st.subheader('Построения timeseries_plot city-temp')
    city = st.selectbox("Выберите город для построения графика t(C)-date", data.city.unique())
    data['rolling_mean'] = data.groupby('city')['temperature'].transform(lambda x: x.rolling(window=30).mean())
    data['rolling_std'] = data.groupby('city')['temperature'].transform(lambda x: x.rolling(window=30).std())
    stats = process_temperature_data_v2(data)
    data_city = data[data.city == city]    
    data_city['anomaly'] = (data_city['temperature'] - data_city['rolling_mean']).abs() > 2 * data_city['rolling_std']
    
    
    strat_date, end_date = st.date_input(
            'Выберите временной отрезок данных', 
            (datetime.datetime(2010, 1, 1).date(), datetime.datetime.now().date()), 
            format="MM.DD.YYYY")
    data_city_date_slice = data_city[
        (data_city.timestamp > pd.Timestamp(strat_date))&(data_city.timestamp < pd.Timestamp(end_date))
        ]

    if st.button(f"Построить график исторических данных для {city}"):
        fig, ax = plt.subplots()
        plt.fill_between(
            data_city_date_slice['timestamp'],
            data_city_date_slice['rolling_mean'] - data_city_date_slice['rolling_std'],
            data_city_date_slice['rolling_mean'] + data_city_date_slice['rolling_std'],
            color='pink', alpha=0.25)
        sns.lineplot(x='timestamp', y='rolling_mean', color='skyblue', data=data_city_date_slice)
        plt.scatter(
            data_city_date_slice[data_city_date_slice['anomaly']]['timestamp'], 
            data_city_date_slice[data_city_date_slice['anomaly']]['temperature'], 
            color='red', 
            label='Anomaly', 
            marker='o', 
            s=2)
        plt.title(f't(°C)-date for {city}')
        plt.xlabel('date')
        plt.ylabel('t(°C)')
        st.pyplot(fig)
    
    if st.button(f"Показать описательные статистики для {city}"):
        
        st.write(f'avg_min_temperature={stats.get(city).get("min"):.3f}')
        st.write(f'avg_max_temperature={stats.get(city).get("max"):.3f}')
        for s in data.season.unique():
            st.write(f'Среднесезонная температура {s} = {stats.get(city).get("season_avg").get(s):.3f} (trend: {stats.get(city).get("trend").get(s)})')

    api_key = st.text_input(label="Введение ваш API_key для OpenWeatherMap API")
    if api_key: 
        weather_city = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric')
        if weather_city.status_code != 200:
            raise ValueError('{"cod":401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}')
        temp_now = weather_city.json().get('main').get('temp')
        season = season_now()
        season_stat = data_city.groupby('season').agg({'temperature':['mean', 'std']}).loc[season]['temperature']
        
        st.write(f'Температура в {city} сейчаc {temp_now:.2f}°C ({"" if abs(temp_now - season_stat["mean"]) > season_stat["std"] * 2 else 'не'} аномальна)')
        st.write(f'Исторические показатели для данного сезона {season_stat["mean"]:.3f}±{season_stat["std"]:.3f}')        
        
    
    
else:
    st.write("Пожалуйста, загрузите CSV-файл.")
    