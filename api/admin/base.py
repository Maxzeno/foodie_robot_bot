"""
Base admin utilities, mixins, and widgets for GeoJSON fields with map previews.
Uses Leaflet.js (free, no API key required) for map rendering.
"""
import json
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class GeoJSONPointWidget(forms.Widget):
    """
    Interactive map widget for GeoJSON Point fields.
    Users can click on the map to set the location.
    """
    template_name = 'django/forms/widgets/textarea.html'

    def __init__(self, attrs=None, default_center=None, default_zoom=6):
        self.default_center = default_center or [9.0820, 8.6753]  # Nigeria center
        self.default_zoom = default_zoom
        super().__init__(attrs=attrs)

    def format_value(self, value):
        if value and isinstance(value, dict):
            return json.dumps(value, indent=2)
        elif value and isinstance(value, str):
            try:
                parsed = json.loads(value)
                return json.dumps(parsed, indent=2)
            except (json.JSONDecodeError, TypeError):
                return value
        return value or ''

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}

        # Parse existing value
        current_coords = None
        if value:
            try:
                if isinstance(value, str):
                    data = json.loads(value)
                else:
                    data = value
                if data and data.get('type') == 'Point':
                    current_coords = data.get('coordinates', [])
            except (json.JSONDecodeError, TypeError):
                pass

        # Generate unique ID
        widget_id = attrs.get('id', f'id_{name}')
        map_id = f'{widget_id}_map'

        # Determine initial center and zoom
        if current_coords and len(current_coords) >= 2:
            center_lat, center_lng = current_coords[1], current_coords[0]
            zoom = 15
        else:
            center_lat, center_lng = self.default_center
            zoom = self.default_zoom

        # Format value for textarea
        formatted_value = self.format_value(value)

        html = f'''
        <div style="margin-bottom: 15px;">
            <div id="{map_id}" style="height: 350px; border-radius: 8px; border: 2px solid #dee2e6; margin-bottom: 10px;"></div>
            <div style="display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 150px;">
                    <label style="font-size: 12px; color: #666;">Longitude:</label>
                    <input type="number" step="any" id="{widget_id}_lng"
                           style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
                           placeholder="-180 to 180" />
                </div>
                <div style="flex: 1; min-width: 150px;">
                    <label style="font-size: 12px; color: #666;">Latitude:</label>
                    <input type="number" step="any" id="{widget_id}_lat"
                           style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
                           placeholder="-90 to 90" />
                </div>
                <div style="display: flex; align-items: end; gap: 5px;">
                    <button type="button" onclick="setPointFromInputs_{widget_id}()"
                            style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Set Location
                    </button>
                    <button type="button" onclick="clearPoint_{widget_id}()"
                            style="padding: 8px 16px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Clear
                    </button>
                </div>
            </div>
            <details style="margin-top: 10px;">
                <summary style="cursor: pointer; color: #666; font-size: 12px;">Show/Edit Raw JSON</summary>
                <textarea name="{name}" id="{widget_id}" rows="4"
                          style="width: 100%; font-family: monospace; font-size: 12px; margin-top: 5px; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
                >{formatted_value}</textarea>
            </details>
        </div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        (function() {{
            var checkLeaflet = setInterval(function() {{
                if (typeof L !== 'undefined') {{
                    clearInterval(checkLeaflet);
                    initPointMap_{widget_id}();
                }}
            }}, 100);

            var map_{widget_id}, marker_{widget_id};

            function initPointMap_{widget_id}() {{
                map_{widget_id} = L.map('{map_id}').setView([{center_lat}, {center_lng}], {zoom});
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap'
                }}).addTo(map_{widget_id});

                // Add existing marker if coords exist
                var textarea = document.getElementById('{widget_id}');
                try {{
                    var data = JSON.parse(textarea.value);
                    if (data && data.type === 'Point' && data.coordinates) {{
                        var lng = data.coordinates[0];
                        var lat = data.coordinates[1];
                        marker_{widget_id} = L.marker([lat, lng], {{draggable: true}}).addTo(map_{widget_id});
                        document.getElementById('{widget_id}_lng').value = lng;
                        document.getElementById('{widget_id}_lat').value = lat;
                        marker_{widget_id}.on('dragend', function(e) {{
                            var pos = e.target.getLatLng();
                            updatePoint_{widget_id}(pos.lng, pos.lat);
                        }});
                    }}
                }} catch(e) {{}}

                // Click to set marker
                map_{widget_id}.on('click', function(e) {{
                    updatePoint_{widget_id}(e.latlng.lng, e.latlng.lat);
                }});
            }}

            window.updatePoint_{widget_id} = function(lng, lat) {{
                if (marker_{widget_id}) {{
                    map_{widget_id}.removeLayer(marker_{widget_id});
                }}
                marker_{widget_id} = L.marker([lat, lng], {{draggable: true}}).addTo(map_{widget_id});
                marker_{widget_id}.on('dragend', function(e) {{
                    var pos = e.target.getLatLng();
                    updatePoint_{widget_id}(pos.lng, pos.lat);
                }});

                document.getElementById('{widget_id}_lng').value = lng.toFixed(6);
                document.getElementById('{widget_id}_lat').value = lat.toFixed(6);

                var geojson = {{
                    "type": "Point",
                    "coordinates": [lng, lat]
                }};
                document.getElementById('{widget_id}').value = JSON.stringify(geojson, null, 2);
            }};

            window.setPointFromInputs_{widget_id} = function() {{
                var lng = parseFloat(document.getElementById('{widget_id}_lng').value);
                var lat = parseFloat(document.getElementById('{widget_id}_lat').value);
                if (!isNaN(lng) && !isNaN(lat) && lng >= -180 && lng <= 180 && lat >= -90 && lat <= 90) {{
                    updatePoint_{widget_id}(lng, lat);
                    map_{widget_id}.setView([lat, lng], 15);
                }} else {{
                    alert('Invalid coordinates. Longitude: -180 to 180, Latitude: -90 to 90');
                }}
            }};

            window.clearPoint_{widget_id} = function() {{
                if (marker_{widget_id}) {{
                    map_{widget_id}.removeLayer(marker_{widget_id});
                    marker_{widget_id} = null;
                }}
                document.getElementById('{widget_id}_lng').value = '';
                document.getElementById('{widget_id}_lat').value = '';
                document.getElementById('{widget_id}').value = '';
            }};
        }})();
        </script>
        '''
        return mark_safe(html)


class GeoJSONPolygonWidget(forms.Widget):
    """
    Interactive map widget for GeoJSON Polygon fields.
    Users can draw a polygon on the map.
    """
    template_name = 'django/forms/widgets/textarea.html'

    def __init__(self, attrs=None, default_center=None, default_zoom=6):
        self.default_center = default_center or [9.0820, 8.6753]  # Nigeria center
        self.default_zoom = default_zoom
        super().__init__(attrs=attrs)

    def format_value(self, value):
        if value and isinstance(value, dict):
            return json.dumps(value, indent=2)
        elif value and isinstance(value, str):
            try:
                parsed = json.loads(value)
                return json.dumps(parsed, indent=2)
            except (json.JSONDecodeError, TypeError):
                return value
        return value or ''

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}

        # Parse existing value
        current_polygon = None
        if value:
            try:
                if isinstance(value, str):
                    data = json.loads(value)
                else:
                    data = value
                if data and data.get('type') == 'Polygon':
                    current_polygon = data
            except (json.JSONDecodeError, TypeError):
                pass

        # Generate unique ID
        widget_id = attrs.get('id', f'id_{name}')
        map_id = f'{widget_id}_map'

        # Determine initial center
        center_lat, center_lng = self.default_center
        zoom = self.default_zoom
        if current_polygon:
            coords = current_polygon.get('coordinates', [[]])[0]
            if coords:
                lngs = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                center_lng = sum(lngs) / len(lngs)
                center_lat = sum(lats) / len(lats)
                zoom = 12

        # Format value for textarea
        formatted_value = self.format_value(value)
        polygon_json = json.dumps(current_polygon) if current_polygon else 'null'

        html = f'''
        <div style="margin-bottom: 15px;">
            <div style="background: #e9ecef; padding: 10px; border-radius: 8px 8px 0 0; font-size: 13px;">
                <strong>Instructions:</strong> Click points on the map to draw boundary. Click first point again to close.
            </div>
            <div id="{map_id}" style="height: 400px; border: 2px solid #dee2e6; border-top: none;"></div>
            <div style="display: flex; gap: 10px; margin: 10px 0;">
                <button type="button" onclick="clearPolygon_{widget_id}()"
                        style="padding: 8px 16px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Clear Boundary
                </button>
                <button type="button" onclick="undoLastPoint_{widget_id}()"
                        style="padding: 8px 16px; background: #ffc107; color: black; border: none; border-radius: 4px; cursor: pointer;">
                    Undo Last Point
                </button>
                <span id="{widget_id}_status" style="padding: 8px; color: #666;"></span>
            </div>
            <details style="margin-top: 10px;">
                <summary style="cursor: pointer; color: #666; font-size: 12px;">Show/Edit Raw JSON</summary>
                <textarea name="{name}" id="{widget_id}" rows="8"
                          style="width: 100%; font-family: monospace; font-size: 12px; margin-top: 5px; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
                >{formatted_value}</textarea>
            </details>
        </div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        (function() {{
            var checkLeaflet = setInterval(function() {{
                if (typeof L !== 'undefined') {{
                    clearInterval(checkLeaflet);
                    initPolygonMap_{widget_id}();
                }}
            }}, 100);

            var map_{widget_id}, polygon_{widget_id}, points_{widget_id} = [], markers_{widget_id} = [], polyline_{widget_id};

            function initPolygonMap_{widget_id}() {{
                map_{widget_id} = L.map('{map_id}').setView([{center_lat}, {center_lng}], {zoom});
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap'
                }}).addTo(map_{widget_id});

                // Load existing polygon
                var existingPolygon = {polygon_json};
                if (existingPolygon && existingPolygon.coordinates && existingPolygon.coordinates[0]) {{
                    var coords = existingPolygon.coordinates[0];
                    // Don't include the closing point in our points array
                    for (var i = 0; i < coords.length - 1; i++) {{
                        points_{widget_id}.push([coords[i][1], coords[i][0]]);
                    }}
                    drawPolygon_{widget_id}();
                    updateStatus_{widget_id}();
                }}

                // Click to add points
                map_{widget_id}.on('click', function(e) {{
                    // Check if clicking near first point to close
                    if (points_{widget_id}.length >= 3) {{
                        var firstPoint = points_{widget_id}[0];
                        var dist = map_{widget_id}.distance(e.latlng, L.latLng(firstPoint[0], firstPoint[1]));
                        if (dist < 50) {{ // Within 50 meters
                            closePolygon_{widget_id}();
                            return;
                        }}
                    }}

                    points_{widget_id}.push([e.latlng.lat, e.latlng.lng]);
                    drawPolygon_{widget_id}();
                    updateStatus_{widget_id}();
                    savePolygon_{widget_id}();
                }});
            }}

            function drawPolygon_{widget_id}() {{
                // Clear existing
                markers_{widget_id}.forEach(function(m) {{ map_{widget_id}.removeLayer(m); }});
                markers_{widget_id} = [];
                if (polyline_{widget_id}) map_{widget_id}.removeLayer(polyline_{widget_id});
                if (polygon_{widget_id}) map_{widget_id}.removeLayer(polygon_{widget_id});

                if (points_{widget_id}.length === 0) return;

                // Draw markers
                points_{widget_id}.forEach(function(p, i) {{
                    var color = i === 0 ? 'green' : 'blue';
                    var marker = L.circleMarker([p[0], p[1]], {{
                        radius: 8, fillColor: color, color: '#fff', weight: 2, fillOpacity: 0.8
                    }}).addTo(map_{widget_id});
                    if (i === 0) marker.bindTooltip('Start (click to close)', {{permanent: false}});
                    markers_{widget_id}.push(marker);
                }});

                // Draw polygon or polyline
                if (points_{widget_id}.length >= 3) {{
                    polygon_{widget_id} = L.polygon(points_{widget_id}, {{
                        color: '#3388ff', weight: 3, fillOpacity: 0.2
                    }}).addTo(map_{widget_id});
                }} else {{
                    polyline_{widget_id} = L.polyline(points_{widget_id}, {{
                        color: '#3388ff', weight: 3
                    }}).addTo(map_{widget_id});
                }}
            }}

            function closePolygon_{widget_id}() {{
                if (points_{widget_id}.length >= 3) {{
                    savePolygon_{widget_id}();
                    drawPolygon_{widget_id}();
                }}
            }}

            function savePolygon_{widget_id}() {{
                if (points_{widget_id}.length < 3) {{
                    document.getElementById('{widget_id}').value = '';
                    return;
                }}

                var coords = points_{widget_id}.map(function(p) {{ return [p[1], p[0]]; }});
                // Close the ring
                coords.push(coords[0]);

                var geojson = {{
                    "type": "Polygon",
                    "coordinates": [coords]
                }};
                document.getElementById('{widget_id}').value = JSON.stringify(geojson, null, 2);
            }}

            function updateStatus_{widget_id}() {{
                var status = document.getElementById('{widget_id}_status');
                var count = points_{widget_id}.length;
                if (count < 3) {{
                    status.textContent = count + ' points (need at least 3)';
                    status.style.color = '#dc3545';
                }} else {{
                    status.textContent = count + ' points - boundary set!';
                    status.style.color = '#28a745';
                }}
            }}

            window.clearPolygon_{widget_id} = function() {{
                points_{widget_id} = [];
                drawPolygon_{widget_id}();
                updateStatus_{widget_id}();
                document.getElementById('{widget_id}').value = '';
            }};

            window.undoLastPoint_{widget_id} = function() {{
                if (points_{widget_id}.length > 0) {{
                    points_{widget_id}.pop();
                    drawPolygon_{widget_id}();
                    updateStatus_{widget_id}();
                    savePolygon_{widget_id}();
                }}
            }};
        }})();
        </script>
        '''
        return mark_safe(html)


class GeoJSONFieldMixin:
    """
    Mixin that adds map preview functionality for GeoJSON Point and Polygon fields.

    Usage:
        class MyAdmin(GeoJSONFieldMixin, admin.ModelAdmin):
            geojson_point_fields = ['point', 'location']
            geojson_polygon_fields = ['boundary']
    """
    geojson_point_fields = []
    geojson_polygon_fields = []

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in self.geojson_point_fields:
            kwargs['widget'] = GeoJSONPointWidget
        elif db_field.name in self.geojson_polygon_fields:
            kwargs['widget'] = GeoJSONPolygonWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


def render_point_map_preview(point_data, field_name='point', height=300):
    """
    Render a map preview for a GeoJSON Point.

    Args:
        point_data: dict with GeoJSON Point format or None
        field_name: str for unique element IDs
        height: int for map height in pixels

    Returns:
        SafeString with HTML for the map preview
    """
    if not point_data or not isinstance(point_data, dict):
        return format_html(
            '<div style="padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; color: #6c757d;">'
            'No location set</div>'
        )

    try:
        coords = point_data.get('coordinates', [])
        if len(coords) < 2:
            return format_html('<div style="color: #dc3545;">Invalid coordinates</div>')

        lng, lat = coords[0], coords[1]
        map_id = f"map_{field_name}_{id(point_data)}"

        return format_html('''
            <div style="margin: 10px 0;">
                <div style="background: #e9ecef; padding: 10px; border-radius: 8px 8px 0 0; font-family: monospace; font-size: 13px;">
                    <strong>Coordinates:</strong> {}, {} (lng, lat)
                </div>
                <div id="{}" style="height: {}px; border-radius: 0 0 8px 8px; border: 1px solid #dee2e6;"></div>
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <script>
                    (function() {{
                        setTimeout(function() {{
                            if (typeof L !== 'undefined') {{
                                var map = L.map('{}').setView([{}, {}], 15);
                                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                                    attribution: '&copy; OpenStreetMap contributors'
                                }}).addTo(map);
                                L.marker([{}, {}]).addTo(map)
                                    .bindPopup('Location').openPopup();
                            }}
                        }}, 100);
                    }})();
                </script>
            </div>
        ''', lng, lat, map_id, height, map_id, lat, lng, lat, lng)
    except Exception as e:
        return format_html('<div style="color: #dc3545;">Error rendering map: {}</div>', str(e))


def render_polygon_map_preview(polygon_data, field_name='boundary', height=400):
    """
    Render a map preview for a GeoJSON Polygon.

    Args:
        polygon_data: dict with GeoJSON Polygon format or None
        field_name: str for unique element IDs
        height: int for map height in pixels

    Returns:
        SafeString with HTML for the map preview
    """
    if not polygon_data or not isinstance(polygon_data, dict):
        return format_html(
            '<div style="padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; color: #6c757d;">'
            'No boundary set</div>'
        )

    try:
        coords = polygon_data.get('coordinates', [[]])
        if not coords or not coords[0]:
            return format_html('<div style="color: #dc3545;">Invalid polygon coordinates</div>')

        # Calculate center and bounds
        ring = coords[0]
        lngs = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        center_lng = sum(lngs) / len(lngs)
        center_lat = sum(lats) / len(lats)

        # Convert to JSON for JavaScript
        geojson_str = json.dumps(polygon_data)
        map_id = f"map_{field_name}_{id(polygon_data)}"

        # Pre-format numbers for format_html
        center_lng_str = f"{center_lng:.4f}"
        center_lat_str = f"{center_lat:.4f}"

        return format_html('''
            <div style="margin: 10px 0;">
                <div style="background: #e9ecef; padding: 10px; border-radius: 8px 8px 0 0; font-family: monospace; font-size: 13px;">
                    <strong>Boundary:</strong> {} points | Center: {}, {}
                </div>
                <div id="{}" style="height: {}px; border-radius: 0 0 8px 8px; border: 1px solid #dee2e6;"></div>
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <script>
                    (function() {{
                        setTimeout(function() {{
                            if (typeof L !== 'undefined') {{
                                var map = L.map('{}').setView([{}, {}], 12);
                                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                                    attribution: '&copy; OpenStreetMap contributors'
                                }}).addTo(map);
                                var geojson = {};
                                var layer = L.geoJSON(geojson, {{
                                    style: {{
                                        color: '#3388ff',
                                        weight: 3,
                                        fillOpacity: 0.2
                                    }}
                                }}).addTo(map);
                                map.fitBounds(layer.getBounds());
                            }}
                        }}, 100);
                    }})();
                </script>
            </div>
        ''', len(ring), center_lng_str, center_lat_str, map_id, height, map_id, center_lat, center_lng, mark_safe(geojson_str))
    except Exception as e:
        return format_html('<div style="color: #dc3545;">Error rendering map: {}</div>', str(e))


def render_geojson_display(data, field_name='geojson'):
    """
    Render a pretty-printed GeoJSON display.
    """
    if not data:
        return format_html('<span style="color: #6c757d;">Not set</span>')

    try:
        if isinstance(data, str):
            data = json.loads(data)

        pretty_json = json.dumps(data, indent=2)
        return format_html(
            '<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px; '
            'font-size: 12px; max-height: 200px; overflow: auto; margin: 0;">{}</pre>',
            pretty_json
        )
    except Exception:
        return format_html('<span style="color: #dc3545;">Invalid JSON</span>')
