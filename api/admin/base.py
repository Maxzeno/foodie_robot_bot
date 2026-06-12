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
            except:
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
    Advanced interactive map widget for GeoJSON Polygon fields.
    Features:
    - Click to add points
    - Drag points to reposition
    - Click points to select/delete
    - Click edges to insert new points
    - Undo/redo functionality
    - Area calculation
    - Zoom to fit
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
            except:
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
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px; border-radius: 8px 8px 0 0; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="font-size: 13px;">
                        <strong>🗺️ Advanced Boundary Editor</strong>
                        <div style="font-size: 11px; opacity: 0.9; margin-top: 3px;">
                            Click to add • Drag to move • Click point to select/delete • Click edge to insert
                        </div>
                    </div>
                    <div id="{widget_id}_info" style="text-align: right; font-size: 12px; background: rgba(255,255,255,0.2); padding: 6px 12px; border-radius: 4px;">
                        <div id="{widget_id}_points_count">0 points</div>
                        <div id="{widget_id}_area" style="font-size: 11px; opacity: 0.9;">Area: --</div>
                    </div>
                </div>
            </div>
            <div id="{map_id}" style="height: 500px; border: 2px solid #667eea; border-top: none; position: relative;"></div>

            <!-- Control Panel -->
            <div style="background: #f8f9fa; padding: 12px; border: 2px solid #dee2e6; border-top: none; border-radius: 0 0 8px 8px;">
                <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                    <!-- Drawing Tools -->
                    <div style="display: flex; gap: 5px;">
                        <button type="button" onclick="setMode_{widget_id}('draw')" id="{widget_id}_btn_draw"
                                style="padding: 8px 14px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;">
                            ✏️ Draw
                        </button>
                        <button type="button" onclick="setMode_{widget_id}('edit')" id="{widget_id}_btn_edit"
                                style="padding: 8px 14px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;">
                            ✋ Edit
                        </button>
                    </div>

                    <div style="border-left: 2px solid #dee2e6; height: 30px;"></div>

                    <!-- Edit Tools -->
                    <button type="button" onclick="deleteSelected_{widget_id}()" id="{widget_id}_btn_delete"
                            style="padding: 8px 14px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;" disabled>
                        🗑️ Delete Point
                    </button>
                    <button type="button" onclick="undo_{widget_id}()" id="{widget_id}_btn_undo"
                            style="padding: 8px 14px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;" disabled>
                        ↶ Undo
                    </button>
                    <button type="button" onclick="redo_{widget_id}()" id="{widget_id}_btn_redo"
                            style="padding: 8px 14px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;" disabled>
                        ↷ Redo
                    </button>

                    <div style="border-left: 2px solid #dee2e6; height: 30px;"></div>

                    <!-- Utility Tools -->
                    <button type="button" onclick="zoomToFit_{widget_id}()" id="{widget_id}_btn_zoom"
                            style="padding: 8px 14px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;" disabled>
                        🔍 Zoom to Fit
                    </button>
                    <button type="button" onclick="clearPolygon_{widget_id}()"
                            style="padding: 8px 14px; background: #ffc107; color: black; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;">
                        🗑️ Clear All
                    </button>
                </div>

                <!-- Status Bar -->
                <div id="{widget_id}_status" style="margin-top: 10px; padding: 8px 12px; background: white; border-radius: 4px; font-size: 12px; border: 1px solid #dee2e6;">
                    <span style="color: #666;">Ready to draw. Click on the map to add boundary points.</span>
                </div>
            </div>

            <details style="margin-top: 10px;">
                <summary style="cursor: pointer; color: #666; font-size: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                    📝 Show/Edit Raw GeoJSON
                </summary>
                <textarea name="{name}" id="{widget_id}" rows="8"
                          style="width: 100%; font-family: monospace; font-size: 12px; margin-top: 5px; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
                >{formatted_value}</textarea>
                <button type="button" onclick="loadFromTextarea_{widget_id}()"
                        style="margin-top: 8px; padding: 8px 16px; background: #fd7e14; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;">
                    📥 Load from JSON
                </button>
            </details>
        </div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/leaflet-geometryutil@0.10.1/src/leaflet.geometryutil.js"></script>
        <script>
        (function() {{
            var checkLeaflet = setInterval(function() {{
                if (typeof L !== 'undefined') {{
                    clearInterval(checkLeaflet);
                    initPolygonMap_{widget_id}();
                }}
            }}, 100);

            var map_{widget_id}, polygon_{widget_id}, points_{widget_id} = [],
                markers_{widget_id} = [], midpointMarkers_{widget_id} = [],
                selectedIndex_{widget_id} = null, mode_{widget_id} = 'draw',
                history_{widget_id} = [], historyIndex_{widget_id} = -1;

            function initPolygonMap_{widget_id}() {{
                map_{widget_id} = L.map('{map_id}').setView([{center_lat}, {center_lng}], {zoom});
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap'
                }}).addTo(map_{widget_id});

                // Load existing polygon
                var existingPolygon = {polygon_json};
                if (existingPolygon && existingPolygon.coordinates && existingPolygon.coordinates[0]) {{
                    var coords = existingPolygon.coordinates[0];
                    for (var i = 0; i < coords.length - 1; i++) {{
                        points_{widget_id}.push([coords[i][1], coords[i][0]]);
                    }}
                    saveToHistory_{widget_id}();
                    drawPolygon_{widget_id}();
                    updateUI_{widget_id}();
                }}

                // Map click handler
                map_{widget_id}.on('click', function(e) {{
                    if (mode_{widget_id} === 'draw') {{
                        // Check if clicking near first point to close
                        if (points_{widget_id}.length >= 3) {{
                            var firstPoint = points_{widget_id}[0];
                            var dist = map_{widget_id}.distance(e.latlng, L.latLng(firstPoint[0], firstPoint[1]));
                            if (dist < 50) {{
                                updateStatus_{widget_id}('Polygon closed!', '#28a745');
                                return;
                            }}
                        }}

                        points_{widget_id}.push([e.latlng.lat, e.latlng.lng]);
                        saveToHistory_{widget_id}();
                        drawPolygon_{widget_id}();
                        updateUI_{widget_id}();
                        savePolygon_{widget_id}();
                    }}
                }});

                updateUI_{widget_id}();
            }}

            function drawPolygon_{widget_id}() {{
                // Clear existing layers
                markers_{widget_id}.forEach(function(m) {{ map_{widget_id}.removeLayer(m); }});
                midpointMarkers_{widget_id}.forEach(function(m) {{ map_{widget_id}.removeLayer(m); }});
                markers_{widget_id} = [];
                midpointMarkers_{widget_id} = [];
                if (polygon_{widget_id}) map_{widget_id}.removeLayer(polygon_{widget_id});

                if (points_{widget_id}.length === 0) return;

                // Draw vertex markers
                points_{widget_id}.forEach(function(p, i) {{
                    var isSelected = i === selectedIndex_{widget_id};
                    var isFirst = i === 0;
                    var color = isSelected ? 'red' : (isFirst ? '#28a745' : '#3388ff');
                    var radius = isSelected ? 10 : 8;

                    var marker = L.circleMarker([p[0], p[1]], {{
                        radius: radius,
                        fillColor: color,
                        color: '#fff',
                        weight: 2,
                        fillOpacity: 0.9,
                        draggable: false
                    }}).addTo(map_{widget_id});

                    // Tooltip with point number
                    var label = isFirst ? 'Start Point' : 'Point ' + (i + 1);
                    if (isSelected) label += ' (Selected)';
                    marker.bindTooltip(label, {{permanent: false}});

                    // Click to select
                    marker.on('click', function(e) {{
                        L.DomEvent.stopPropagation(e);
                        if (mode_{widget_id} === 'edit') {{
                            selectedIndex_{widget_id} = i;
                            drawPolygon_{widget_id}();
                            updateUI_{widget_id}();
                            updateStatus_{widget_id}('Point ' + (i + 1) + ' selected. Click "Delete Point" to remove.', '#17a2b8');
                        }}
                    }});

                    // Make draggable in edit mode
                    if (mode_{widget_id} === 'edit') {{
                        marker.dragging = new L.Handler.MarkerDrag(marker);
                        marker.dragging.enable();

                        marker.on('drag', function(e) {{
                            var pos = e.target.getLatLng();
                            points_{widget_id}[i] = [pos.lat, pos.lng];
                            drawPolygon_{widget_id}();
                        }});

                        marker.on('dragend', function(e) {{
                            saveToHistory_{widget_id}();
                            savePolygon_{widget_id}();
                            updateUI_{widget_id}();
                            updateStatus_{widget_id}('Point moved!', '#28a745');
                        }});
                    }}

                    markers_{widget_id}.push(marker);
                }});

                // Draw polygon
                if (points_{widget_id}.length >= 3) {{
                    polygon_{widget_id} = L.polygon(points_{widget_id}, {{
                        color: '#3388ff',
                        weight: 3,
                        fillOpacity: 0.2
                    }}).addTo(map_{widget_id});

                    // Add midpoint markers for inserting new points
                    if (mode_{widget_id} === 'edit') {{
                        for (var i = 0; i < points_{widget_id}.length; i++) {{
                            var p1 = points_{widget_id}[i];
                            var p2 = points_{widget_id}[(i + 1) % points_{widget_id}.length];
                            var midLat = (p1[0] + p2[0]) / 2;
                            var midLng = (p1[1] + p2[1]) / 2;

                            var midMarker = L.circleMarker([midLat, midLng], {{
                                radius: 6,
                                fillColor: '#ffc107',
                                color: '#fff',
                                weight: 2,
                                fillOpacity: 0.7,
                                draggable: false
                            }}).addTo(map_{widget_id});

                            midMarker.bindTooltip('Click to insert point', {{permanent: false}});

                            (function(insertIndex) {{
                                midMarker.on('click', function(e) {{
                                    L.DomEvent.stopPropagation(e);
                                    var pos = e.target.getLatLng();
                                    points_{widget_id}.splice(insertIndex + 1, 0, [pos.lat, pos.lng]);
                                    saveToHistory_{widget_id}();
                                    drawPolygon_{widget_id}();
                                    updateUI_{widget_id}();
                                    savePolygon_{widget_id}();
                                    updateStatus_{widget_id}('Point inserted!', '#28a745');
                                }});
                            }})(i);

                            midpointMarkers_{widget_id}.push(midMarker);
                        }}
                    }}
                }} else if (points_{widget_id}.length > 0) {{
                    // Draw polyline if less than 3 points
                    polygon_{widget_id} = L.polyline(points_{widget_id}, {{
                        color: '#3388ff',
                        weight: 3
                    }}).addTo(map_{widget_id});
                }}
            }}

            function savePolygon_{widget_id}() {{
                if (points_{widget_id}.length < 3) {{
                    document.getElementById('{widget_id}').value = '';
                    return;
                }}

                var coords = points_{widget_id}.map(function(p) {{ return [p[1], p[0]]; }});
                coords.push(coords[0]); // Close the ring

                var geojson = {{
                    "type": "Polygon",
                    "coordinates": [coords]
                }};
                document.getElementById('{widget_id}').value = JSON.stringify(geojson, null, 2);
            }}

            function updateUI_{widget_id}() {{
                var count = points_{widget_id}.length;

                // Update points count
                document.getElementById('{widget_id}_points_count').textContent = count + ' point' + (count !== 1 ? 's' : '');

                // Calculate and display area
                if (count >= 3) {{
                    try {{
                        var areaM2 = L.GeometryUtil.geodesicArea(points_{widget_id}.map(function(p) {{
                            return L.latLng(p[0], p[1]);
                        }}));
                        var areaKm2 = (areaM2 / 1000000).toFixed(2);
                        document.getElementById('{widget_id}_area').textContent = 'Area: ' + areaKm2 + ' km²';
                    }} catch(e) {{
                        // Fallback if GeometryUtil not available
                        document.getElementById('{widget_id}_area').textContent = 'Area: Calculated';
                    }}
                }} else {{
                    document.getElementById('{widget_id}_area').textContent = 'Area: --';
                }}

                // Update button states
                document.getElementById('{widget_id}_btn_delete').disabled = selectedIndex_{widget_id} === null || count <= 3;
                document.getElementById('{widget_id}_btn_undo').disabled = historyIndex_{widget_id} <= 0;
                document.getElementById('{widget_id}_btn_redo').disabled = historyIndex_{widget_id} >= history_{widget_id}.length - 1;
                document.getElementById('{widget_id}_btn_zoom').disabled = count < 3;

                // Update mode buttons
                document.getElementById('{widget_id}_btn_draw').style.opacity = mode_{widget_id} === 'draw' ? '1' : '0.6';
                document.getElementById('{widget_id}_btn_edit').style.opacity = mode_{widget_id} === 'edit' ? '1' : '0.6';
            }}

            function updateStatus_{widget_id}(message, color) {{
                var status = document.getElementById('{widget_id}_status');
                status.innerHTML = '<span style="color: ' + (color || '#666') + ';">' + message + '</span>';
            }}

            function saveToHistory_{widget_id}() {{
                // Remove any history after current index
                history_{widget_id} = history_{widget_id}.slice(0, historyIndex_{widget_id} + 1);
                // Add current state
                history_{widget_id}.push(JSON.parse(JSON.stringify(points_{widget_id})));
                historyIndex_{widget_id} = history_{widget_id}.length - 1;
                updateUI_{widget_id}();
            }}

            window.setMode_{widget_id} = function(mode) {{
                mode_{widget_id} = mode;
                selectedIndex_{widget_id} = null;
                drawPolygon_{widget_id}();
                updateUI_{widget_id}();

                if (mode === 'draw') {{
                    updateStatus_{widget_id}('Draw mode: Click on map to add points.', '#28a745');
                }} else {{
                    updateStatus_{widget_id}('Edit mode: Drag points to move, click points to select, click edges to insert.', '#17a2b8');
                }}
            }};

            window.deleteSelected_{widget_id} = function() {{
                if (selectedIndex_{widget_id} !== null && points_{widget_id}.length > 3) {{
                    points_{widget_id}.splice(selectedIndex_{widget_id}, 1);
                    selectedIndex_{widget_id} = null;
                    saveToHistory_{widget_id}();
                    drawPolygon_{widget_id}();
                    updateUI_{widget_id}();
                    savePolygon_{widget_id}();
                    updateStatus_{widget_id}('Point deleted!', '#dc3545');
                }}
            }};

            window.undo_{widget_id} = function() {{
                if (historyIndex_{widget_id} > 0) {{
                    historyIndex_{widget_id}--;
                    points_{widget_id} = JSON.parse(JSON.stringify(history_{widget_id}[historyIndex_{widget_id}]));
                    selectedIndex_{widget_id} = null;
                    drawPolygon_{widget_id}();
                    updateUI_{widget_id}();
                    savePolygon_{widget_id}();
                    updateStatus_{widget_id}('Undo successful!', '#6c757d');
                }}
            }};

            window.redo_{widget_id} = function() {{
                if (historyIndex_{widget_id} < history_{widget_id}.length - 1) {{
                    historyIndex_{widget_id}++;
                    points_{widget_id} = JSON.parse(JSON.stringify(history_{widget_id}[historyIndex_{widget_id}]));
                    selectedIndex_{widget_id} = null;
                    drawPolygon_{widget_id}();
                    updateUI_{widget_id}();
                    savePolygon_{widget_id}();
                    updateStatus_{widget_id}('Redo successful!', '#6c757d');
                }}
            }};

            window.zoomToFit_{widget_id} = function() {{
                if (polygon_{widget_id}) {{
                    map_{widget_id}.fitBounds(polygon_{widget_id}.getBounds(), {{padding: [50, 50]}});
                    updateStatus_{widget_id}('Zoomed to boundary!', '#007bff');
                }}
            }};

            window.clearPolygon_{widget_id} = function() {{
                if (points_{widget_id}.length > 0 && !confirm('Are you sure you want to clear the entire boundary?')) {{
                    return;
                }}
                points_{widget_id} = [];
                selectedIndex_{widget_id} = null;
                history_{widget_id} = [];
                historyIndex_{widget_id} = -1;
                saveToHistory_{widget_id}();
                drawPolygon_{widget_id}();
                updateUI_{widget_id}();
                document.getElementById('{widget_id}').value = '';
                updateStatus_{widget_id}('Boundary cleared. Ready to draw.', '#ffc107');
            }};

            window.loadFromTextarea_{widget_id} = function() {{
                try {{
                    var text = document.getElementById('{widget_id}').value.trim();
                    if (!text) {{
                        updateStatus_{widget_id}('No JSON to load! Paste GeoJSON into the textarea first.', '#dc3545');
                        return;
                    }}

                    var data = JSON.parse(text);

                    // Validate GeoJSON format
                    if (!data || data.type !== 'Polygon' || !data.coordinates || !data.coordinates[0]) {{
                        updateStatus_{widget_id}('Invalid GeoJSON Polygon format! Must be: {{"type":"Polygon","coordinates":[[[lng,lat],...]]}}', '#dc3545');
                        return;
                    }}

                    // Clear existing points and load new ones
                    points_{widget_id} = [];
                    var coords = data.coordinates[0];
                    for (var i = 0; i < coords.length - 1; i++) {{
                        points_{widget_id}.push([coords[i][1], coords[i][0]]);
                    }}

                    // Update history and redraw
                    history_{widget_id} = [];
                    historyIndex_{widget_id} = -1;
                    saveToHistory_{widget_id}();
                    drawPolygon_{widget_id}();
                    updateUI_{widget_id}();

                    // Zoom to fit the new boundary
                    if (polygon_{widget_id}) {{
                        map_{widget_id}.fitBounds(polygon_{widget_id}.getBounds(), {{padding: [50, 50]}});
                    }}

                    updateStatus_{widget_id}('✅ GeoJSON loaded successfully! ' + points_{widget_id}.length + ' points loaded onto map.', '#28a745');
                }} catch(error) {{
                    updateStatus_{widget_id}('❌ Invalid JSON format! Error: ' + error.message, '#dc3545');
                    console.error('GeoJSON load error:', error);
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
