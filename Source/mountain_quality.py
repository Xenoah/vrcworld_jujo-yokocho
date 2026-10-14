"""Deterministic source-stage integration for the selected mountain revision."""
from mountain_quality_contract import flags
from mountain_detail import apply_mountain_detail
from mountain_snow_craft import apply_mountain_snow_craft
from fantasy_landscape import apply_snow_deposition


def apply_mountain_quality(g,features):
    """Run after landscape(), before compact/color baking, with strict flags.

    Legacy feature-off behavior uses the original snow function unchanged.
    Seam normals are separately computed from quantized export coordinates.
    """
    adaptive,snow,craft,normals=flags(features)
    detail_stats=apply_mountain_detail(g) if adaptive else None
    snow_stats=None
    if craft:snow_stats=apply_mountain_snow_craft(g,'soft')
    elif snow:apply_snow_deposition(g)
    return detail_stats,snow_stats
