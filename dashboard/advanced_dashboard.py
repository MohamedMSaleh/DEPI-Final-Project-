"""
Advanced Professional IoT Dashboard
Enterprise-grade monitoring system with fixed layout and interactive controls
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, func
from pathlib import Path
import sys

# Setup paths
sys.path.append(str(Path(__file__).parent.parent))
from database.schema import (
    get_session, FactWeatherReading, DimTime, DimSensor, 
    DimLocation, DimStatus, AlertLog
)

# Database setup
DB_PATH = Path(__file__).parent.parent / "database" / "iot_warehouse.db"
DB_ENGINE = create_engine(f"sqlite:///{DB_PATH}")

# External stylesheets
FONT_AWESOME_URL = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"

# Initialize Dash app with custom configuration
app = dash.Dash(
    __name__,
    external_stylesheets=[FONT_AWESOME_URL],
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}]
)
app.title = "IoT Advanced Dashboard"

# Custom CSS for better styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
        .dash-dropdown {
            font-family: inherit !important;
        }
        .Select-control {
            background-color: #252b48 !important;
            border: 1px solid #374151 !important;
            color: #ffffff !important;
        }
        .Select-placeholder {
            color: #b8bcc8 !important;
        }
        .Select-value-label {
            color: #ffffff !important;
        }
        .Select-arrow-zone {
            border-left: 1px solid #374151 !important;
        }
        .Select-menu-outer {
            background-color: #252b48 !important;
            border: 1px solid #374151 !important;
        }
        .Select-option {
            background-color: #252b48 !important;
            color: #ffffff !important;
        }
        .Select-option:hover {
            background-color: #3b82f6 !important;
        }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Custom CSS for dropdowns
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
        .dash-dropdown {
            font-family: inherit !important;
        }
        .Select-control {
            background-color: #252b48 !important;
            border: 1px solid #374151 !important;
            color: #ffffff !important;
        }
        .Select-placeholder {
            color: #ffffff !important;
        }
        .Select-value-label {
            color: #ffffff !important;
        }
        .Select-input {
            color: #ffffff !important;
        }
        .Select-input > input {
            color: #ffffff !important;
        }
        .Select-arrow-zone {
            border-left: 1px solid #374151 !important;
        }
        .Select-menu-outer {
            background-color: #252b48 !important;
            border: 1px solid #374151 !important;
        }
        .Select-menu {
            background-color: #252b48 !important;
        }
        .Select-option {
            background-color: #252b48 !important;
            color: #ffffff !important;
            padding: 8px 10px !important;
        }
        .Select-option:hover {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }
        .Select-option.is-focused {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }
        .Select-option.is-selected {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }
        .VirtualizedSelectOption {
            color: #ffffff !important;
        }
        div[class*="option"] {
            color: #ffffff !important;
        }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Professional color scheme
COLORS = {
    'bg_primary': '#0a0e27',
    'bg_secondary': '#1a1f3a',
    'bg_card': '#252b48',
    'text_primary': '#ffffff',
    'text_secondary': '#b8bcc8',
    'accent_blue': '#3b82f6',
    'accent_green': '#10b981',
    'accent_yellow': '#f59e0b',
    'accent_red': '#ef4444',
    'border': '#374151',
    'gradient_start': '#3b82f6',
    'gradient_end': '#8b5cf6'
}

# Typical climate profiles for monitored cities (used for expected daily range)
CITY_CLIMATE = {
    'Cairo': {'day': 28.0, 'night': 18.0},
    'Alexandria': {'day': 26.0, 'night': 20.0},
    'Giza': {'day': 29.0, 'night': 19.0},
    'Luxor': {'day': 35.0, 'night': 22.0},
    'Aswan': {'day': 38.0, 'night': 24.0}
}


def get_expected_temperature_range(city_name: str) -> tuple[float, float]:
    """Return expected low/high temperature for the given city or all cities."""
    if city_name and city_name != 'all':
        profile = CITY_CLIMATE.get(city_name)
        if profile:
            return profile['night'], profile['day']
    # Fallback: aggregate across all cities
    lows = [profile['night'] for profile in CITY_CLIMATE.values()]
    highs = [profile['day'] for profile in CITY_CLIMATE.values()]
    return min(lows), max(highs)

# Shared styles
CARD_STYLE = {
    'backgroundColor': COLORS['bg_card'],
    'borderRadius': '12px',
    'padding': '20px',
    'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.3)',
    'border': f'1px solid {COLORS["border"]}',
    'height': '100%',
    'display': 'flex',
    'flexDirection': 'column'
}

HEADER_STYLE = {
    'color': COLORS['text_primary'],
    'fontSize': '18px',
    'fontWeight': '600',
    'marginBottom': '15px',
    'marginTop': '0'
}

ICON_STYLE = {
    'color': COLORS['accent_blue'],
    'fontSize': '18px',
    'display': 'inline-block'
}


def section_heading(icon_class: str, title: str, color: str | None = None) -> html.Div:
    """Reusable heading with an icon and text."""
    return html.Div(
        style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginBottom': '15px'},
        children=[
            html.I(className=f"fa-solid {icon_class}", style={**ICON_STYLE, 'color': color or ICON_STYLE['color']}),
            html.H3(title, style=HEADER_STYLE)
        ]
    )

# Layout with responsive viewport
app.layout = html.Div(
    style={
        'backgroundColor': COLORS['bg_primary'],
        'minHeight': '100vh',
        'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        'display': 'flex',
        'flexDirection': 'column'
    },
    children=[
        # Fixed Header
        html.Div(
            style={
                'backgroundColor': COLORS['bg_secondary'],
                'padding': '20px 30px',
                'borderBottom': f'2px solid {COLORS["accent_blue"]}',
                'boxShadow': '0 2px 8px rgba(0, 0, 0, 0.3)',
                'flex': '0 0 auto',
                'zIndex': '100'
            },
            children=[
                html.Div(
                    style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'},
                    children=[
                        html.Div([
                            html.H1(
                                'IoT Weather Monitoring System',
                                style={
                                    'color': COLORS['text_primary'],
                                    'margin': '0',
                                    'fontSize': '28px',
                                    'fontWeight': '700',
                                    'background': f'linear-gradient(135deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]})',
                                    'WebkitBackgroundClip': 'text',
                                    'WebkitTextFillColor': 'transparent',
                                    'backgroundClip': 'text'
                                }
                            ),
                            html.P(
                                'Real-Time Environmental Data Analytics | DEPI Final Project',
                                style={
                                    'color': COLORS['text_secondary'],
                                    'margin': '5px 0 0 0',
                                    'fontSize': '14px'
                                }
                            )
                        ]),
                        html.Div(
                            id='header-status',
                            style={
                                'display': 'flex',
                                'gap': '20px',
                                'alignItems': 'center'
                            }
                        )
                    ]
                )
            ]
        ),
        
        # Control Panel
        html.Div(
            style={
                'backgroundColor': COLORS['bg_secondary'],
                'padding': '15px 30px',
                'borderBottom': f'1px solid {COLORS["border"]}',
                'flex': '0 0 auto'
            },
            children=[
                html.Div(
                    style={'display': 'flex', 'gap': '20px', 'alignItems': 'center', 'flexWrap': 'wrap'},
                    children=[
                        html.Div([
                            html.Label('Select City:', style={'color': COLORS['text_secondary'], 'fontSize': '12px', 'marginBottom': '5px', 'display': 'block'}),
                            dcc.Dropdown(
                                id='city-filter',
                                placeholder='Select a City',
                                style={'width': '200px'},
                                className='custom-dropdown'
                            )
                        ]),
                        html.Div([
                            html.Label('Time Range:', style={'color': COLORS['text_secondary'], 'fontSize': '12px', 'marginBottom': '5px', 'display': 'block'}),
                            dcc.Dropdown(
                                id='time-filter',
                                options=[
                                    {'label': 'Last Hour', 'value': '1h'},
                                    {'label': 'Last 6 Hours', 'value': '6h'},
                                    {'label': 'Last 24 Hours', 'value': '24h'},
                                    {'label': 'Last 7 Days', 'value': '7d'},
                                    {'label': 'All Time', 'value': 'all'}
                                ],
                                value='all',
                                style={'width': '180px'},
                                clearable=False,
                                className='custom-dropdown'
                            )
                        ]),
                        html.Button(
                            [html.I(className='fa-solid fa-refresh', style={'marginRight': '8px'}), 'Refresh Now'],
                            id='refresh-button',
                            n_clicks=0,
                            style={
                                'backgroundColor': COLORS['accent_blue'],
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '6px',
                                'padding': '10px 20px',
                                'cursor': 'pointer',
                                'fontSize': '14px',
                                'fontWeight': '600',
                                'marginTop': '17px',
                                'transition': 'all 0.3s'
                            }
                        )
                    ]
                )
            ]
        ),
        
        # Auto-refresh interval
        dcc.Interval(
            id='interval-update',
            interval=10*1000,  # 10 seconds - faster refresh
            n_intervals=0
        ),
        
        # Main scrollable content
        html.Div(
            style={
                'flex': '1 1 auto',
                'overflow': 'visible',
                'padding': '20px',
                'position': 'relative'
            },
            children=[
                # KPI Cards Row
                html.Div(
                    id='kpi-cards',
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))',
                        'gap': '15px',
                        'marginBottom': '20px'
                    }
                ),
                
                # Main Charts Row
                html.Div(
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fit, minmax(350px, 1fr))',
                        'gap': '15px',
                        'marginBottom': '20px'
                    },
                    children=[
                        # Time Series Chart
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '400px'},
                            children=[
                                section_heading('fa-chart-line', 'Temperature Trends'),
                                dcc.Loading(
                                    type='circle',
                                    color=COLORS['accent_blue'],
                                    children=dcc.Graph(
                                        id='temperature-timeseries',
                                        config={'displayModeBar': False, 'responsive': True},
                                        style={'height': '350px', 'width': '100%'}
                                    )
                                )
                            ]
                        ),
                        
                        # Current Status
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'visible', 'minHeight': '400px'},
                            children=[
                                section_heading('fa-gauge-high', 'Current Readings', COLORS['accent_green']),
                                html.Div(id='current-readings', style={'flex': '1', 'overflow': 'visible'})
                            ]
                        )
                    ]
                ),
                
                # ML Predictions Row
                html.Div(
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': '1fr 1fr',
                        'gap': '15px',
                        'marginBottom': '20px'
                    },
                    children=[
                        # Temperature Predictions Chart
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '400px'},
                            children=[
                                section_heading('fa-brain', 'AI Temperature Predictions', COLORS['gradient_end']),
                                dcc.Loading(
                                    type='circle',
                                    color=COLORS['gradient_end'],
                                    children=dcc.Graph(
                                        id='ml-predictions-chart',
                                        config={'displayModeBar': False, 'responsive': True},
                                        style={'height': '350px', 'width': '100%'}
                                    )
                                )
                            ]
                        ),
                        
                        # Prediction Accuracy & Info
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'visible', 'minHeight': '400px'},
                            children=[
                                section_heading('fa-chart-simple', 'Model Performance', COLORS['accent_green']),
                                html.Div(id='ml-accuracy-info', style={'flex': '1', 'overflow': 'visible'})
                            ]
                        )
                    ]
                ),
                
                # Gauges Row
                html.Div(
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))',
                        'gap': '15px',
                        'marginBottom': '20px'
                    },
                    children=[
                        # Temperature Gauge
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '250px'},
                            children=[
                                html.Div(
                                    style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '15px'},
                                    children=[
                                        html.I(className='fa-solid fa-temperature-three-quarters', style={'color': COLORS['accent_red'], 'fontSize': '20px'}),
                                        html.H3('Avg Temperature', style={**HEADER_STYLE, 'textAlign': 'center', 'fontSize': '16px', 'marginBottom': '0'})
                                    ]
                                ),
                                dcc.Graph(
                                    id='gauge-temperature',
                                    config={'displayModeBar': False},
                                    style={'height': '200px', 'width': '100%'}
                                )
                            ]
                        ),
                        # Humidity Gauge
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '250px'},
                            children=[
                                html.Div(
                                    style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '15px'},
                                    children=[
                                        html.I(className='fa-solid fa-droplet', style={'color': COLORS['accent_blue'], 'fontSize': '20px'}),
                                        html.H3('Avg Humidity', style={**HEADER_STYLE, 'textAlign': 'center', 'fontSize': '16px', 'marginBottom': '0'})
                                    ]
                                ),
                                dcc.Graph(
                                    id='gauge-humidity',
                                    config={'displayModeBar': False},
                                    style={'height': '200px', 'width': '100%'}
                                )
                            ]
                        ),
                        # Wind Gauge
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '250px'},
                            children=[
                                html.Div(
                                    style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '15px'},
                                    children=[
                                        html.I(className='fa-solid fa-wind', style={'color': COLORS['accent_green'], 'fontSize': '20px'}),
                                        html.H3('Avg Wind Speed', style={**HEADER_STYLE, 'textAlign': 'center', 'fontSize': '16px', 'marginBottom': '0'})
                                    ]
                                ),
                                dcc.Graph(
                                    id='gauge-wind',
                                    config={'displayModeBar': False},
                                    style={'height': '200px', 'width': '100%'}
                                )
                            ]
                        ),
                        # Pressure Gauge
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '250px'},
                            children=[
                                html.Div(
                                    style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '15px'},
                                    children=[
                                        html.I(className='fa-solid fa-gauge', style={'color': COLORS['accent_yellow'], 'fontSize': '20px'}),
                                        html.H3('Avg Pressure', style={**HEADER_STYLE, 'textAlign': 'center', 'fontSize': '16px', 'marginBottom': '0'})
                                    ]
                                ),
                                dcc.Graph(
                                    id='gauge-pressure',
                                    config={'displayModeBar': False},
                                    style={'height': '200px', 'width': '100%'}
                                )
                            ]
                        )
                    ]
                ),
                
                # Analytics Row
                html.Div(
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fit, minmax(350px, 1fr))',
                        'gap': '15px',
                        'marginBottom': '20px'
                    },
                    children=[
                        # City Comparison
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '350px'},
                            children=[
                                section_heading('fa-chart-bar', 'City Comparison'),
                                dcc.Graph(
                                    id='city-comparison',
                                    config={'displayModeBar': False},
                                    style={'height': '300px', 'width': '100%'}
                                )
                            ]
                        ),
                        # Distribution
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'hidden', 'minHeight': '350px'},
                            children=[
                                section_heading('fa-chart-area', 'Temperature Distribution', COLORS['accent_green']),
                                dcc.Graph(
                                    id='temp-distribution',
                                    config={'displayModeBar': False},
                                    style={'height': '300px', 'width': '100%'}
                                )
                            ]
                        )
                    ]
                ),
                
                # Alerts and Data Tables
                html.Div(
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fit, minmax(350px, 1fr))',
                        'gap': '15px',
                        'marginBottom': '20px'
                    },
                    children=[
                        # Alerts
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'visible', 'minHeight': '400px'},
                            children=[
                                section_heading('fa-bell', 'Recent Alerts', COLORS['accent_red']),
                                html.Div(
                                    id='alerts-container',
                                    style={'overflow': 'visible', 'flex': '1'}
                                )
                            ]
                        ),
                        # Recent Data
                        html.Div(
                            style={**CARD_STYLE, 'overflow': 'visible', 'minHeight': '400px'},
                            children=[
                                section_heading('fa-table', 'Recent Readings'),
                                html.Div(
                                    id='readings-container',
                                    style={'overflow': 'visible', 'flex': '1'}
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        
        # Fixed Footer
        html.Div(
            style={
                'backgroundColor': COLORS['bg_secondary'],
                'padding': '15px 30px',
                'borderTop': f'1px solid {COLORS["border"]}',
                'textAlign': 'center',
                'flex': '0 0 auto'
            },
            children=[
                html.P(
                    id='footer-text',
                    style={'color': COLORS['text_secondary'], 'margin': '0', 'fontSize': '13px'}
                )
            ]
        )
    ]
)

# ==================== CALLBACKS ====================

# Initialize filters
@app.callback(
    [Output('city-filter', 'options'),
     Output('city-filter', 'value')],
    [Input('interval-update', 'n_intervals')]
)
def update_filters(n):
    """Populate filter dropdowns"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        # Get unique cities
        cities = session.query(DimLocation.city_name).distinct().all()
        city_options = [
            {'label': city[0], 'value': city[0]} for city in cities
        ]
        
        # Set default to Cairo if available, otherwise first city
        default_city = 'Cairo' if any(city[0] == 'Cairo' for city in cities) else (cities[0][0] if cities else None)
        
        return city_options, default_city
        
    except Exception as e:
        print(f"Error updating filters: {e}")
        return [{'label': 'All', 'value': 'all'}], 'Cairo'
    finally:
        session.close()

# Header status
@app.callback(
    Output('header-status', 'children'),
    [Input('interval-update', 'n_intervals')]
)
def update_header_status(n):
    """Update header with system status"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        active_sensors = session.query(DimSensor).filter(DimSensor.is_active == True).count()
        open_alerts = session.query(AlertLog).filter(AlertLog.is_resolved == False).count()
        
        return [
            html.Div([
                html.I(className='fa-solid fa-check-circle', style={'fontSize': '12px', 'color': COLORS['accent_green'], 'marginRight': '5px'}),
                html.Span(f'{active_sensors} Active Sensors', style={'color': COLORS['accent_green'], 'fontSize': '14px', 'fontWeight': '600'})
            ]),
            html.Div([
                html.I(className='fa-solid fa-triangle-exclamation', style={'fontSize': '12px', 'color': COLORS['accent_yellow'], 'marginRight': '5px'}),
                html.Span(f'{open_alerts} Open Alerts', style={'color': COLORS['accent_yellow'], 'fontSize': '14px', 'fontWeight': '600'})
            ])
        ]
    except:
        return []
    finally:
        session.close()

# KPI Cards
@app.callback(
    Output('kpi-cards', 'children'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value'),
     Input('time-filter', 'value')]
)
def update_kpi_cards(n, clicks, city, time_range):
    """Update KPI summary cards"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        # Build query
        query = session.query(FactWeatherReading).join(
            DimLocation, FactWeatherReading.location_id == DimLocation.location_id
        ).join(
            DimSensor, FactWeatherReading.sensor_id == DimSensor.sensor_id
        ).join(
            DimTime, FactWeatherReading.time_id == DimTime.time_id
        )
        
        # Apply filters
        if city and city != 'all':
            query = query.filter(DimLocation.city_name == city)
        
        # Time filter - only apply if not 'all'
        if time_range and time_range != 'all':
            time_map = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}
            hours = time_map.get(time_range, 24)
            cutoff = datetime.now() - timedelta(hours=hours)
            query = query.filter(DimTime.ts >= cutoff)
        
        readings = query.all()
        
        if not readings:
            return [html.Div('No data available', style={'color': COLORS['text_secondary']})]
        
        # Calculate metrics
        total = len(readings)
        anomalies = sum(1 for r in readings if r.is_anomaly)

        temps = [r.temperature for r in readings if r.temperature is not None]
        humidities = [r.humidity for r in readings if r.humidity is not None]
        winds = [r.wind_speed for r in readings if r.wind_speed is not None]
        pressures = [r.pressure for r in readings if r.pressure is not None]

        avg_temp = sum(temps) / len(temps) if temps else 0.0
        avg_humidity = sum(humidities) / len(humidities) if humidities else 0.0
        avg_wind = sum(winds) / len(winds) if winds else 0.0
        avg_pressure = sum(pressures) / len(pressures) if pressures else 0.0

        observed_high = max(temps) if temps else None
        observed_low = min(temps) if temps else None

        expected_low, expected_high = get_expected_temperature_range(city or 'all')
        observed_range = (
            f"{observed_low:.1f}°C" if observed_low is not None else "--",
            f"{observed_high:.1f}°C" if observed_high is not None else "--"
        )

        kpis = [
            {'icon': 'fa-database', 'label': 'Total Readings', 'value': f'{total:,}', 'color': COLORS['accent_blue']},
            {'icon': 'fa-bolt', 'label': 'Anomalies', 'value': f'{anomalies}', 'color': COLORS['accent_red']},
            {'icon': 'fa-temperature-half', 'label': 'Observed Range', 'value': f'{observed_range[0]} to {observed_range[1]}', 'color': COLORS['accent_green']},
            {'icon': 'fa-droplet', 'label': 'Avg Humidity', 'value': f'{avg_humidity:.0f}%', 'color': COLORS['accent_blue']},
            {'icon': 'fa-wind', 'label': 'Avg Wind Speed', 'value': f'{avg_wind:.1f} km/h', 'color': COLORS['accent_green']},
            {'icon': 'fa-gauge-high', 'label': 'Avg Pressure', 'value': f'{avg_pressure:.0f} hPa', 'color': COLORS['accent_yellow']}
        ]
        
        cards = []
        for kpi in kpis:
            cards.append(
                html.Div(
                    style={
                        **CARD_STYLE,
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'textAlign': 'center',
                        'borderLeft': f'4px solid {kpi["color"]}'
                    },
                    children=[
                        html.I(className=f"fa-solid {kpi['icon']}", style={'fontSize': '32px', 'marginBottom': '10px', 'color': kpi['color']}),
                        html.Div(kpi['value'], style={'fontSize': '24px', 'fontWeight': '700', 'color': kpi['color'], 'marginBottom': '5px'}),
                        html.Div(kpi['label'], style={'fontSize': '12px', 'color': COLORS['text_secondary'], 'textTransform': 'uppercase', 'letterSpacing': '1px'})
                    ]
                )
            )
        
        return cards
        
    except Exception as e:
        print(f"Error in KPI cards: {e}")
        return [html.Div(f'Error: {str(e)}', style={'color': COLORS['accent_red']})]
    finally:
        session.close()

# Temperature Timeseries
@app.callback(
    Output('temperature-timeseries', 'figure'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value'),
     Input('time-filter', 'value')]
)
def update_timeseries(n, clicks, city, time_range):
    """Update temperature timeseries chart"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        # Build query
        query = session.query(
            DimTime.ts,
            DimLocation.city_name,
            FactWeatherReading.temperature
        ).join(
            FactWeatherReading, DimTime.time_id == FactWeatherReading.time_id
        ).join(
            DimLocation, FactWeatherReading.location_id == DimLocation.location_id
        ).join(
            DimSensor, FactWeatherReading.sensor_id == DimSensor.sensor_id
        )
        
        # Apply filters
        if city and city != 'all':
            query = query.filter(DimLocation.city_name == city)
        
        # Time filter - only apply if not 'all'
        if time_range and time_range != 'all':
            time_map = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}
            hours = time_map.get(time_range, 24)
            cutoff = datetime.now() - timedelta(hours=hours)
            query = query.filter(DimTime.ts >= cutoff)
        
        results = query.order_by(DimTime.ts).all()
        
        if not results:
            return go.Figure().update_layout(
                paper_bgcolor=COLORS['bg_card'],
                plot_bgcolor=COLORS['bg_card'],
                font={'color': COLORS['text_secondary']},
                xaxis={'visible': False},
                yaxis={'visible': False},
                annotations=[{
                    'text': 'No data available',
                    'xref': 'paper',
                    'yref': 'paper',
                    'showarrow': False,
                    'font': {'size': 14, 'color': COLORS['text_secondary']}
                }]
            )
        
        df = pd.DataFrame(results, columns=['timestamp', 'city', 'temperature'])
        
        fig = go.Figure()
        
        for city_name in df['city'].unique():
            city_data = df[df['city'] == city_name]
            fig.add_trace(go.Scatter(
                x=city_data['timestamp'],
                y=city_data['temperature'],
                name=city_name,
                mode='lines+markers',
                line={'width': 2},
                marker={'size': 4}
            ))
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg_card'],
            plot_bgcolor=COLORS['bg_card'],
            font={'color': COLORS['text_primary'], 'size': 11},
            xaxis={
                'showgrid': True,
                'gridcolor': COLORS['border'],
                'title': None,
                'color': COLORS['text_secondary']
            },
            yaxis={
                'showgrid': True,
                'gridcolor': COLORS['border'],
                'title': 'Temperature (°C)',
                'color': COLORS['text_secondary']
            },
            legend={
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': 1.02,
                'xanchor': 'right',
                'x': 1,
                'font': {'size': 10}
            },
            margin={'l': 50, 'r': 20, 't': 40, 'b': 40},
            hovermode='x unified',
            autosize=True
        )
        
        return fig
        
    except Exception as e:
        print(f"Error in timeseries: {e}")
        return go.Figure()
    finally:
        session.close()

# Current Readings
@app.callback(
    Output('current-readings', 'children'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value')]
)
def update_current_readings(n, clicks, city):
    """Display current readings as cards"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        query = session.query(
            DimLocation.city_name,
            FactWeatherReading.temperature,
            FactWeatherReading.humidity,
            FactWeatherReading.wind_speed,
            FactWeatherReading.pressure,
            DimTime.ts
        ).join(
            FactWeatherReading, DimLocation.location_id == FactWeatherReading.location_id
        ).join(
            DimTime, FactWeatherReading.time_id == DimTime.time_id
        )
        
        # Only show data if a city is selected
        if not city or city == 'all':
            return html.Div('Please select a city to view current conditions', style={'color': COLORS['text_secondary'], 'textAlign': 'center', 'padding': '20px'})
        
        # Filter for the selected city only
        query = query.filter(DimLocation.city_name == city)
        
        # Get latest reading for the selected city
        subquery = session.query(
            FactWeatherReading.location_id,
            func.max(DimTime.ts).label('max_ts')
        ).join(
            DimTime, FactWeatherReading.time_id == DimTime.time_id
        ).group_by(FactWeatherReading.location_id).subquery()
        
        query = query.join(
            subquery,
            (FactWeatherReading.location_id == subquery.c.location_id) &
            (DimTime.ts == subquery.c.max_ts)
        )
        
        results = query.distinct().limit(1).all()
        
        if not results:
            return html.Div('No current data', style={'color': COLORS['text_secondary'], 'textAlign': 'center', 'padding': '20px'})
        
        # Get the single result (only one city)
        city_name, temp, humidity, wind, pressure, ts = results[0]
        
        # Create the centered design matching the image
        return html.Div(
            style={
                'display': 'flex',
                'flexDirection': 'column',
                'alignItems': 'center',
                'justifyContent': 'center',
                'height': '100%',
                'padding': '20px'
            },
            children=[
                # City name with location pin
                html.Div(
                    style={'textAlign': 'center', 'marginBottom': '20px'},
                    children=[
                        html.I(className='fa-solid fa-location-dot', style={'fontSize': '20px', 'color': COLORS['accent_blue'], 'marginRight': '8px'}),
                        html.Span(city_name, style={
                            'color': COLORS['accent_blue'],
                            'fontSize': '22px',
                            'fontWeight': '600'
                        })
                    ]
                ),
                
                # Large temperature display
                html.Div(
                    f'{temp:.1f}°C',
                    style={
                        'fontSize': '64px',
                        'fontWeight': '700',
                        'color': '#f59e0b',
                        'marginBottom': '25px',
                        'textAlign': 'center'
                    }
                ),
                
                # Horizontal separator
                html.Hr(style={
                    'width': '100%',
                    'border': 'none',
                    'borderTop': f'1px solid {COLORS["border"]}',
                    'margin': '20px 0'
                }),
                
                # Metrics list
                html.Div(
                    style={'width': '100%'},
                    children=[
                        # Humidity
                        html.Div(
                            style={
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'alignItems': 'center',
                                'padding': '12px 0',
                                'borderBottom': f'1px solid {COLORS["border"]}'
                            },
                            children=[
                                html.Div([
                                    html.I(className='fa-solid fa-droplet', style={'fontSize': '16px', 'marginRight': '8px', 'color': COLORS['accent_blue']}),
                                    html.Span('Humidity:', style={
                                        'color': COLORS['text_primary'],
                                        'fontSize': '15px'
                                    })
                                ]),
                                html.Span(f'{humidity:.0f}%', style={
                                    'color': COLORS['accent_blue'],
                                    'fontSize': '16px',
                                    'fontWeight': '600'
                                })
                            ]
                        ),
                        
                        # Wind
                        html.Div(
                            style={
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'alignItems': 'center',
                                'padding': '12px 0',
                                'borderBottom': f'1px solid {COLORS["border"]}'
                            },
                            children=[
                                html.Div([
                                    html.I(className='fa-solid fa-wind', style={'fontSize': '16px', 'marginRight': '8px', 'color': COLORS['accent_green']}),
                                    html.Span('Wind:', style={
                                        'color': COLORS['text_primary'],
                                        'fontSize': '15px'
                                    })
                                ]),
                                html.Span(f'{wind:.1f} km/h', style={
                                    'color': COLORS['accent_green'],
                                    'fontSize': '16px',
                                    'fontWeight': '600'
                                })
                            ]
                        ),
                        
                        # Pressure
                        html.Div(
                            style={
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'alignItems': 'center',
                                'padding': '12px 0'
                            },
                            children=[
                                html.Div([
                                    html.I(className='fa-solid fa-gauge', style={'fontSize': '16px', 'marginRight': '8px', 'color': '#f59e0b'}),
                                    html.Span('Pressure:', style={
                                        'color': COLORS['text_primary'],
                                        'fontSize': '15px'
                                    })
                                ]),
                                html.Span(f'{pressure:.0f} hPa', style={
                                    'color': '#f59e0b',
                                    'fontSize': '16px',
                                    'fontWeight': '600'
                                })
                            ]
                        ),
                        
                        # Updated timestamp
                        html.Div(
                            f'Updated: {ts.strftime("%H:%M:%S")}',
                            style={
                                'textAlign': 'center',
                                'color': COLORS['text_secondary'],
                                'fontSize': '13px',
                                'marginTop': '20px'
                            }
                        )
                    ]
                )
            ]
        )
        
    except Exception as e:
        print(f"Error in current readings: {e}")
        return html.Div(f'Error: {str(e)}', style={'color': COLORS['accent_red']})
    finally:
        session.close()

# Gauges
@app.callback(
    [Output('gauge-temperature', 'figure'),
     Output('gauge-humidity', 'figure'),
     Output('gauge-wind', 'figure'),
     Output('gauge-pressure', 'figure')],
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value'),
     Input('time-filter', 'value')]
)
def update_gauges(n, clicks, city, time_range):
    """Update all gauge charts"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        query = session.query(
            FactWeatherReading.temperature,
            FactWeatherReading.humidity,
            FactWeatherReading.wind_speed,
            FactWeatherReading.pressure
        ).join(
            DimLocation, FactWeatherReading.location_id == DimLocation.location_id
        ).join(
            DimTime, FactWeatherReading.time_id == DimTime.time_id
        )
        
        if city and city != 'all':
            query = query.filter(DimLocation.city_name == city)
        
        # Time filter - only apply if not 'all'
        if time_range and time_range != 'all':
            time_map = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}
            hours = time_map.get(time_range, 24)
            cutoff = datetime.now() - timedelta(hours=hours)
            query = query.filter(DimTime.ts >= cutoff)
        
        results = query.all()
        
        if not results:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                paper_bgcolor=COLORS['bg_card'],
                plot_bgcolor=COLORS['bg_card']
            )
            return empty_fig, empty_fig, empty_fig, empty_fig
        
        temps = [r[0] for r in results if r[0] is not None]
        humids = [r[1] for r in results if r[1] is not None]
        winds = [r[2] for r in results if r[2] is not None]
        pressures = [r[3] for r in results if r[3] is not None]
        
        avg_temp = sum(temps) / len(temps) if temps else 0
        avg_humidity = sum(humids) / len(humids) if humids else 0
        avg_wind = sum(winds) / len(winds) if winds else 0
        avg_pressure = sum(pressures) / len(pressures) if pressures else 0
        
        def create_gauge(value, title, range_vals, color):
            fig = go.Figure(go.Indicator(
                mode='gauge+number',
                value=value,
                number={'font': {'size': 24, 'color': COLORS['text_primary']}},
                gauge={
                    'axis': {'range': range_vals, 'tickcolor': COLORS['text_secondary']},
                    'bar': {'color': color},
                    'bgcolor': COLORS['bg_secondary'],
                    'borderwidth': 0,
                    'steps': [
                        {'range': [range_vals[0], (range_vals[1] - range_vals[0]) * 0.5 + range_vals[0]], 'color': COLORS['bg_secondary']},
                        {'range': [(range_vals[1] - range_vals[0]) * 0.5 + range_vals[0], range_vals[1]], 'color': COLORS['bg_primary']}
                    ]
                }
            ))
            
            fig.update_layout(
                paper_bgcolor=COLORS['bg_card'],
                plot_bgcolor=COLORS['bg_card'],
                font={'color': COLORS['text_primary']},
                margin={'l': 20, 'r': 20, 't': 20, 'b': 20},
                height=200
            )
            
            return fig
        
        temp_fig = create_gauge(avg_temp, 'Temp', [-10, 50], COLORS['accent_red'])
        humidity_fig = create_gauge(avg_humidity, 'Humidity', [0, 100], COLORS['accent_blue'])
        wind_fig = create_gauge(avg_wind, 'Wind', [0, 100], COLORS['accent_green'])
        pressure_fig = create_gauge(avg_pressure, 'Pressure', [950, 1050], COLORS['accent_yellow'])
        
        return temp_fig, humidity_fig, wind_fig, pressure_fig
        
    except Exception as e:
        print(f"Error in gauges: {e}")
        empty_fig = go.Figure()
        empty_fig.update_layout(paper_bgcolor=COLORS['bg_card'], plot_bgcolor=COLORS['bg_card'])
        return empty_fig, empty_fig, empty_fig, empty_fig
    finally:
        session.close()

# City Comparison
@app.callback(
    Output('city-comparison', 'figure'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('time-filter', 'value')]
)
def update_city_comparison(n, clicks, time_range):
    """City comparison bar chart"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        query = session.query(
            DimLocation.city_name,
            func.avg(FactWeatherReading.temperature).label('avg_temp'),
            func.count(FactWeatherReading.reading_id).label('count')
        ).join(
            FactWeatherReading, DimLocation.location_id == FactWeatherReading.location_id
        ).join(
            DimTime, FactWeatherReading.time_id == DimTime.time_id
        )
        
        # Time filter - only apply if not 'all'
        if time_range and time_range != 'all':
            time_map = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}
            hours = time_map.get(time_range, 24)
            cutoff = datetime.now() - timedelta(hours=hours)
            query = query.filter(DimTime.ts >= cutoff)
        
        query = query.group_by(DimLocation.city_name).all()
        
        if not query:
            return go.Figure().update_layout(paper_bgcolor=COLORS['bg_card'], plot_bgcolor=COLORS['bg_card'])
        
        df = pd.DataFrame(query, columns=['city', 'avg_temp', 'count'])
        
        fig = go.Figure(data=[
            go.Bar(
                x=df['city'],
                y=df['avg_temp'],
                marker_color=COLORS['accent_blue'],
                text=df['avg_temp'].round(1),
                textposition='outside',
                textfont={'color': COLORS['text_primary']}
            )
        ])
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg_card'],
            plot_bgcolor=COLORS['bg_card'],
            font={'color': COLORS['text_primary']},
            xaxis={
                'showgrid': False,
                'color': COLORS['text_secondary'],
                'title': None
            },
            yaxis={
                'showgrid': True,
                'gridcolor': COLORS['border'],
                'title': 'Avg Temperature (°C)',
                'color': COLORS['text_secondary']
            },
            margin={'l': 50, 'r': 20, 't': 20, 'b': 40},
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        print(f"Error in city comparison: {e}")
        return go.Figure()
    finally:
        session.close()

# Temperature Distribution
@app.callback(
    Output('temp-distribution', 'figure'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value'),
     Input('time-filter', 'value')]
)
def update_distribution(n, clicks, city, time_range):
    """Temperature distribution histogram"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        query = session.query(
            FactWeatherReading.temperature
        ).join(
            DimLocation, FactWeatherReading.location_id == DimLocation.location_id
        ).join(
            DimTime, FactWeatherReading.time_id == DimTime.time_id
        )
        
        if city and city != 'all':
            query = query.filter(DimLocation.city_name == city)
        
        # Time filter - only apply if not 'all'
        if time_range and time_range != 'all':
            time_map = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}
            hours = time_map.get(time_range, 24)
            cutoff = datetime.now() - timedelta(hours=hours)
            query = query.filter(DimTime.ts >= cutoff)
        
        results = query.all()
        
        if not results:
            return go.Figure().update_layout(paper_bgcolor=COLORS['bg_card'], plot_bgcolor=COLORS['bg_card'])
        
        temps = [r[0] for r in results if r[0] is not None]
        
        fig = go.Figure(data=[
            go.Histogram(
                x=temps,
                marker_color=COLORS['accent_green'],
                nbinsx=20,
                opacity=0.8
            )
        ])
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg_card'],
            plot_bgcolor=COLORS['bg_card'],
            font={'color': COLORS['text_primary']},
            xaxis={
                'showgrid': False,
                'title': 'Temperature (°C)',
                'color': COLORS['text_secondary']
            },
            yaxis={
                'showgrid': True,
                'gridcolor': COLORS['border'],
                'title': 'Frequency',
                'color': COLORS['text_secondary']
            },
            margin={'l': 50, 'r': 20, 't': 20, 'b': 40},
            showlegend=False,
            bargap=0.1
        )
        
        return fig
        
    except Exception as e:
        print(f"Error in distribution: {e}")
        return go.Figure()
    finally:
        session.close()

# Alerts
@app.callback(
    Output('alerts-container', 'children'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks')]
)
def update_alerts(n, clicks):
    """Display recent alerts"""
    session = get_session(DB_ENGINE)
    
    try:
        # Clear session cache to get fresh data
        session.expire_all()
        
        alerts = session.query(AlertLog).order_by(AlertLog.alert_ts.desc()).limit(15).all()
        
        if not alerts:
            return html.Div('No alerts', style={'color': COLORS['text_secondary'], 'textAlign': 'center', 'padding': '20px'})
        
        alert_items = []
        for alert in alerts:
            severity_colors = {
                'CRITICAL': COLORS['accent_red'],
                'WARNING': COLORS['accent_yellow'],
                'INFO': COLORS['accent_blue']
            }
            
            color = severity_colors.get(alert.alert_severity, COLORS['text_secondary'])
            
            alert_items.append(
                html.Div(
                    style={
                        'backgroundColor': COLORS['bg_secondary'],
                        'borderRadius': '6px',
                        'padding': '12px',
                        'marginBottom': '8px',
                        'borderLeft': f'4px solid {color}'
                    },
                    children=[
                        html.Div(
                            style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '6px'},
                            children=[
                                html.Span(
                                    alert.alert_type,
                                    style={'fontWeight': '600', 'color': color, 'fontSize': '13px'}
                                ),
                                html.Span(
                                    alert.alert_ts.strftime('%m/%d %H:%M'),
                                    style={'color': COLORS['text_secondary'], 'fontSize': '11px'}
                                )
                            ]
                        ),
                        html.Div(
                            alert.message,
                            style={'color': COLORS['text_secondary'], 'fontSize': '12px', 'marginBottom': '6px'}
                        ),
                        html.Div(
                            'OK Resolved' if alert.is_resolved else 'WARN Active',
                            style={
                                'fontSize': '11px',
                                'color': COLORS['accent_green'] if alert.is_resolved else COLORS['accent_yellow'],
                                'fontWeight': '600'
                            }
                        )
                    ]
                )
            )
        
        return alert_items
        
    except Exception as e:
        print(f"Error in alerts: {e}")
        return html.Div(f'Error: {str(e)}', style={'color': COLORS['accent_red']})
    finally:
        session.close()

# Recent Readings Table
@app.callback(
    Output('readings-container', 'children'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value')]
)
def update_readings_table(n, clicks, city):
    """Display recent readings in table"""
    session = get_session(DB_ENGINE)
    
    try:
        query = session.query(
            DimTime.ts,
            DimLocation.city_name,
            DimSensor.sensor_type,
            FactWeatherReading.temperature,
            FactWeatherReading.humidity,
            FactWeatherReading.wind_speed
        ).join(
            FactWeatherReading, DimTime.time_id == FactWeatherReading.time_id
        ).join(
            DimLocation, FactWeatherReading.location_id == DimLocation.location_id
        ).join(
            DimSensor, FactWeatherReading.sensor_id == DimSensor.sensor_id
        )
        
        if city and city != 'all':
            query = query.filter(DimLocation.city_name == city)
        
        results = query.order_by(DimTime.ts.desc()).limit(20).all()
        
        if not results:
            return html.Div('No data', style={'color': COLORS['text_secondary'], 'textAlign': 'center', 'padding': '20px'})
        
        df = pd.DataFrame(results, columns=['Time', 'City', 'Sensor', 'Temp (°C)', 'Humidity (%)', 'Wind (km/h)'])
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%m/%d %H:%M')
        df['Temp (°C)'] = df['Temp (°C)'].round(1)
        df['Humidity (%)'] = df['Humidity (%)'].round(0)
        df['Wind (km/h)'] = df['Wind (km/h)'].round(1)
        
        return dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            style_table={'overflowX': 'auto', 'overflowY': 'auto'},
            style_cell={
                'backgroundColor': COLORS['bg_secondary'],
                'color': COLORS['text_primary'],
                'border': f'1px solid {COLORS["border"]}',
                'textAlign': 'left',
                'padding': '10px',
                'fontSize': '12px',
                'fontFamily': 'inherit'
            },
            style_header={
                'backgroundColor': COLORS['bg_primary'],
                'fontWeight': '600',
                'borderBottom': f'2px solid {COLORS["accent_blue"]}',
                'color': COLORS['text_primary']
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': COLORS['bg_card']
                }
            ],
            page_action='none',
            fixed_rows={'headers': True}
        )
        
    except Exception as e:
        print(f"Error in readings table: {e}")
        return html.Div(f'Error: {str(e)}', style={'color': COLORS['accent_red']})
    finally:
        session.close()

# ML Predictions Chart
@app.callback(
    Output('ml-predictions-chart', 'figure'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value')]
)
def update_ml_predictions(n, clicks, city):
    """Update ML predictions chart showing actual vs predicted temperatures"""
    import sqlite3
    
    try:
        # Always create fresh connection to avoid caching
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, isolation_level=None)
        
        # Check if predictions table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_temperature_predictions'")
        if not cursor.fetchone():
            conn.close()
            return go.Figure().update_layout(
                paper_bgcolor=COLORS['bg_card'],
                plot_bgcolor=COLORS['bg_card'],
                font={'color': COLORS['text_secondary']},
                annotations=[{
                    'text': 'No predictions available yet. Run ML model first.',
                    'xref': 'paper',
                    'yref': 'paper',
                    'x': 0.5,
                    'y': 0.5,
                    'showarrow': False,
                    'font': {'size': 14, 'color': COLORS['text_secondary']}
                }]
            )
        
        # Get actual temperatures (last 48 hours)
        actual_query = """
        SELECT 
            t.ts as timestamp,
            l.city_name,
            AVG(f.temperature) as temperature
        FROM fact_weather_reading f
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_location l ON f.location_id = l.location_id
        WHERE t.ts >= datetime('now', '-48 hours')
        """
        if city and city != 'all':
            actual_query += f" AND l.city_name = '{city}'"
        actual_query += " GROUP BY l.city_name, strftime('%Y-%m-%d %H:00:00', t.ts) ORDER BY t.ts"
        
        actual_df = pd.read_sql_query(actual_query, conn)
        
        # Get predictions
        pred_query = """
        SELECT 
            prediction_timestamp as timestamp,
            city_name,
            predicted_temp as temperature,
            lower_bound,
            upper_bound
        FROM ml_temperature_predictions
        WHERE created_at = (SELECT MAX(created_at) FROM ml_temperature_predictions)
        """
        if city and city != 'all':
            pred_query += f" AND city_name = '{city}'"
        pred_query += " ORDER BY prediction_timestamp"
        
        pred_df = pd.read_sql_query(pred_query, conn)
        conn.close()
        
        if actual_df.empty and pred_df.empty:
            return go.Figure().update_layout(
                paper_bgcolor=COLORS['bg_card'],
                plot_bgcolor=COLORS['bg_card'],
                font={'color': COLORS['text_secondary']},
                annotations=[{
                    'text': 'No data available',
                    'xref': 'paper',
                    'yref': 'paper',
                    'x': 0.5,
                    'y': 0.5,
                    'showarrow': False,
                    'font': {'size': 14, 'color': COLORS['text_secondary']}
                }]
            )
        
        actual_df['timestamp'] = pd.to_datetime(actual_df['timestamp'])
        pred_df['timestamp'] = pd.to_datetime(pred_df['timestamp'])
        
        fig = go.Figure()
        
        # Plot actual temperatures
        for city_name in actual_df['city_name'].unique():
            city_data = actual_df[actual_df['city_name'] == city_name]
            fig.add_trace(go.Scatter(
                x=city_data['timestamp'],
                y=city_data['temperature'],
                name=f'{city_name} (Actual)',
                mode='lines+markers',
                line={'width': 2},
                marker={'size': 6}
            ))
        
        # Plot predictions
        for city_name in pred_df['city_name'].unique():
            city_preds = pred_df[pred_df['city_name'] == city_name]
            
            # Prediction line
            fig.add_trace(go.Scatter(
                x=city_preds['timestamp'],
                y=city_preds['temperature'],
                name=f'{city_name} (Predicted)',
                mode='lines+markers',
                line={'width': 2, 'dash': 'dash'},
                marker={'size': 4, 'symbol': 'diamond'}
            ))
            
            # Confidence interval
            fig.add_trace(go.Scatter(
                x=city_preds['timestamp'].tolist() + city_preds['timestamp'].tolist()[::-1],
                y=city_preds['upper_bound'].tolist() + city_preds['lower_bound'].tolist()[::-1],
                fill='toself',
                fillcolor='rgba(128, 128, 128, 0.2)',
                line={'color': 'rgba(255,255,255,0)'},
                showlegend=False,
                name=f'{city_name} CI',
                hoverinfo='skip'
            ))
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg_card'],
            plot_bgcolor=COLORS['bg_card'],
            font={'color': COLORS['text_primary'], 'size': 11},
            xaxis={
                'showgrid': True,
                'gridcolor': COLORS['border'],
                'title': None,
                'color': COLORS['text_secondary']
            },
            yaxis={
                'showgrid': True,
                'gridcolor': COLORS['border'],
                'title': 'Temperature (°C)',
                'color': COLORS['text_secondary']
            },
            legend={
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': 1.02,
                'xanchor': 'right',
                'x': 1,
                'font': {'size': 10}
            },
            margin={'l': 50, 'r': 20, 't': 40, 'b': 40},
            hovermode='x unified',
            autosize=True
        )
        
        return fig
        
    except Exception as e:
        print(f"Error in ML predictions: {e}")
        return go.Figure().update_layout(
            paper_bgcolor=COLORS['bg_card'],
            plot_bgcolor=COLORS['bg_card'],
            font={'color': COLORS['text_secondary']},
            annotations=[{
                'text': f'Error loading predictions: {str(e)}',
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'showarrow': False,
                'font': {'size': 12, 'color': COLORS['accent_red']}
            }]
        )

# ML Accuracy Info
@app.callback(
    Output('ml-accuracy-info', 'children'),
    [Input('interval-update', 'n_intervals'),
     Input('refresh-button', 'n_clicks'),
     Input('city-filter', 'value')]
)
def update_ml_accuracy(n, clicks, city):
    """Display ML model accuracy and information"""
    import sqlite3
    
    try:
        # Always create fresh connection to avoid caching
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        
        # Check if predictions exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_temperature_predictions'")
        if not cursor.fetchone():
            conn.close()
            return html.Div([
                html.Div([
                    html.I(className='fa-solid fa-circle-info', style={'color': COLORS['accent_blue'], 'fontSize': '48px', 'marginBottom': '15px'}),
                    html.H4('No Predictions Yet', style={'color': COLORS['text_primary'], 'marginBottom': '10px'}),
                    html.P('Run the ML prediction model to generate temperature forecasts.', style={'color': COLORS['text_secondary'], 'fontSize': '14px', 'marginBottom': '15px'}),
                    html.Code('python ml/temperature_predictor.py', style={'backgroundColor': COLORS['bg_secondary'], 'padding': '10px', 'borderRadius': '5px', 'display': 'block'})
                ], style={'textAlign': 'center', 'padding': '20px'})
            ])
        
        # Get prediction statistics
        stats_query = """
        SELECT 
            city_name,
            COUNT(*) as num_predictions,
            AVG(predicted_temp) as avg_predicted,
            MIN(predicted_temp) as min_predicted,
            MAX(predicted_temp) as max_predicted,
            MAX(created_at) as last_run
        FROM ml_temperature_predictions
        WHERE created_at = (SELECT MAX(created_at) FROM ml_temperature_predictions)
        """
        if city and city != 'all':
            stats_query += f" AND city_name = '{city}'"
        stats_query += " GROUP BY city_name"
        
        stats_df = pd.read_sql_query(stats_query, conn)
        conn.close()
        
        if stats_df.empty:
            return html.Div('No prediction data available', style={'color': COLORS['text_secondary'], 'textAlign': 'center', 'padding': '20px'})
        
        # Create info cards
        cards = []
        
        # Summary card
        total_predictions = stats_df['num_predictions'].sum()
        num_cities = len(stats_df)
        last_run = pd.to_datetime(stats_df['last_run'].iloc[0]).strftime('%Y-%m-%d %H:%M')
        
        cards.append(html.Div([
            html.Div([
                html.I(className='fa-solid fa-robot', style={'color': COLORS['gradient_end'], 'fontSize': '24px'}),
                html.Div([
                    html.Div(f'{total_predictions}', style={'fontSize': '28px', 'fontWeight': '700', 'color': COLORS['text_primary']}),
                    html.Div('Total Predictions', style={'fontSize': '12px', 'color': COLORS['text_secondary']})
                ], style={'marginLeft': '15px'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '15px'}),
            
            html.Div([
                html.Div([
                    html.Strong('Cities: ', style={'color': COLORS['text_secondary']}),
                    html.Span(f'{num_cities}', style={'color': COLORS['text_primary']})
                ], style={'marginBottom': '5px'}),
                html.Div([
                    html.Strong('Model: ', style={'color': COLORS['text_secondary']}),
                    html.Span('Prophet v1', style={'color': COLORS['accent_green']})
                ], style={'marginBottom': '5px'}),
                html.Div([
                    html.Strong('Last Run: ', style={'color': COLORS['text_secondary']}),
                    html.Span(last_run, style={'color': COLORS['text_primary'], 'fontSize': '11px'})
                ])
            ], style={'fontSize': '13px'})
        ], style={
            'backgroundColor': COLORS['bg_secondary'],
            'borderRadius': '8px',
            'padding': '15px',
            'marginBottom': '15px',
            'border': f'1px solid {COLORS["border"]}'
        }))
        
        # City-specific cards
        for _, row in stats_df.iterrows():
            cards.append(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-location-dot', style={'color': COLORS['accent_blue'], 'fontSize': '18px'}),
                    html.Strong(row['city_name'], style={'fontSize': '16px', 'color': COLORS['text_primary'], 'marginLeft': '10px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                html.Div([
                    html.Div([
                        html.Span('Avg: ', style={'color': COLORS['text_secondary'], 'fontSize': '12px'}),
                        html.Span(f"{row['avg_predicted']:.1f}°C", style={'color': COLORS['text_primary'], 'fontWeight': '600'})
                    ], style={'marginBottom': '3px'}),
                    html.Div([
                        html.Span('Range: ', style={'color': COLORS['text_secondary'], 'fontSize': '12px'}),
                        html.Span(f"{row['min_predicted']:.1f}°C - {row['max_predicted']:.1f}°C", style={'color': COLORS['text_primary']})
                    ])
                ], style={'fontSize': '13px'})
            ], style={
                'backgroundColor': COLORS['bg_secondary'],
                'borderRadius': '8px',
                'padding': '12px',
                'marginBottom': '10px',
                'border': f'1px solid {COLORS["border"]}'
            }))
        
        return html.Div(cards, style={'maxHeight': '320px', 'overflowY': 'auto'})
        
    except Exception as e:
        print(f"Error in ML accuracy: {e}")
        return html.Div(f'Error: {str(e)}', style={'color': COLORS['accent_red'], 'padding': '20px'})

# Footer
@app.callback(
    Output('footer-text', 'children'),
    [Input('interval-update', 'n_intervals')]
)
def update_footer(n):
    """Update footer timestamp"""
    return f'Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Auto-refresh: Every 60 seconds | (c) 2025 DEPI IoT Project'

# ==================== RUN SERVER ====================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("[STARTING] ADVANCED IOT DASHBOARD")
    print("="*60)
    print(f"[URL] Dashboard: http://127.0.0.1:8050")
    print(f"[DB] Database: {DB_PATH}")
    print(f"[REFRESH] Auto-refresh: Every 60 seconds")
    print(f"[STOP] Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(debug=False, host='127.0.0.1', port=8050)
