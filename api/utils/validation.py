"""
GeoJSON validation utilities for Point and Polygon fields.
"""
from django.core.exceptions import ValidationError


def validate_geojson_point(value, field_name="point"):
    """
    Validate that value is a valid GeoJSON Point.

    Expected format:
    {
        "type": "Point",
        "coordinates": [longitude, latitude]
    }

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If the value is not a valid GeoJSON Point
    """
    if value is None:
        return  # Allow null values

    if not isinstance(value, dict):
        raise ValidationError({
            field_name: f"Must be a dictionary/object, got {type(value).__name__}"
        })

    # Check type field
    if "type" not in value:
        raise ValidationError({
            field_name: "Missing 'type' field. Must be 'Point'"
        })

    if value["type"] != "Point":
        raise ValidationError({
            field_name: f"Invalid type '{value['type']}'. Must be 'Point'"
        })

    # Check coordinates field
    if "coordinates" not in value:
        raise ValidationError({
            field_name: "Missing 'coordinates' field"
        })

    coords = value["coordinates"]

    if not isinstance(coords, (list, tuple)):
        raise ValidationError({
            field_name: f"'coordinates' must be a list, got {type(coords).__name__}"
        })

    if len(coords) != 2:
        raise ValidationError({
            field_name: f"'coordinates' must have exactly 2 values [longitude, latitude], got {len(coords)}"
        })

    try:
        longitude = float(coords[0])
        latitude = float(coords[1])
    except (TypeError, ValueError):
        raise ValidationError({
            field_name: "Coordinates must be numeric values"
        })

    # Validate longitude range (-180 to 180)
    if not -180 <= longitude <= 180:
        raise ValidationError({
            field_name: f"Longitude must be between -180 and 180, got {longitude}"
        })

    # Validate latitude range (-90 to 90)
    if not -90 <= latitude <= 90:
        raise ValidationError({
            field_name: f"Latitude must be between -90 and 90, got {latitude}"
        })


def validate_geojson_polygon(value, field_name="boundary"):
    """
    Validate that value is a valid GeoJSON Polygon.

    Expected format:
    {
        "type": "Polygon",
        "coordinates": [
            [[lon1, lat1], [lon2, lat2], [lon3, lat3], [lon1, lat1]]  # Ring (first = last)
        ]
    }

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If the value is not a valid GeoJSON Polygon
    """
    if value is None:
        return  # Allow null values

    if not isinstance(value, dict):
        raise ValidationError({
            field_name: f"Must be a dictionary/object, got {type(value).__name__}"
        })

    # Check type field
    if "type" not in value:
        raise ValidationError({
            field_name: "Missing 'type' field. Must be 'Polygon'"
        })

    if value["type"] != "Polygon":
        raise ValidationError({
            field_name: f"Invalid type '{value['type']}'. Must be 'Polygon'"
        })

    # Check coordinates field
    if "coordinates" not in value:
        raise ValidationError({
            field_name: "Missing 'coordinates' field"
        })

    coords = value["coordinates"]

    if not isinstance(coords, (list, tuple)):
        raise ValidationError({
            field_name: f"'coordinates' must be a list of rings, got {type(coords).__name__}"
        })

    if len(coords) == 0:
        raise ValidationError({
            field_name: "Polygon must have at least one ring (exterior boundary)"
        })

    # Validate each ring
    for ring_idx, ring in enumerate(coords):
        ring_name = "exterior ring" if ring_idx == 0 else f"interior ring {ring_idx}"

        if not isinstance(ring, (list, tuple)):
            raise ValidationError({
                field_name: f"{ring_name} must be a list of coordinates"
            })

        if len(ring) < 4:
            raise ValidationError({
                field_name: f"{ring_name} must have at least 4 coordinates (minimum 3 points + closing point)"
            })

        # Validate each coordinate in the ring
        for coord_idx, coord in enumerate(ring):
            if not isinstance(coord, (list, tuple)):
                raise ValidationError({
                    field_name: f"{ring_name}, position {coord_idx}: coordinate must be a list [longitude, latitude]"
                })

            if len(coord) < 2:
                raise ValidationError({
                    field_name: f"{ring_name}, position {coord_idx}: coordinate must have at least 2 values [longitude, latitude]"
                })

            try:
                longitude = float(coord[0])
                latitude = float(coord[1])
            except (TypeError, ValueError):
                raise ValidationError({
                    field_name: f"{ring_name}, position {coord_idx}: coordinates must be numeric values"
                })

            # Validate longitude range
            if not -180 <= longitude <= 180:
                raise ValidationError({
                    field_name: f"{ring_name}, position {coord_idx}: longitude must be between -180 and 180, got {longitude}"
                })

            # Validate latitude range
            if not -90 <= latitude <= 90:
                raise ValidationError({
                    field_name: f"{ring_name}, position {coord_idx}: latitude must be between -90 and 90, got {latitude}"
                })

        # Check that first and last coordinates are the same (ring is closed)
        first_coord = ring[0]
        last_coord = ring[-1]

        if first_coord[0] != last_coord[0] or first_coord[1] != last_coord[1]:
            raise ValidationError({
                field_name: f"{ring_name}: ring must be closed (first and last coordinates must be identical)"
            })
