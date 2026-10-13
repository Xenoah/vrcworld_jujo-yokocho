"""One authored left staff entrance per shop, guest stations intact.

Introduced in v2.8; the v2.7 baseline is kept separately for exact comparison.
All values are shop-local metres, Z-up. No floor, post or guest-station change.
"""
COUNTER_TRIM=.30
COUNTER_SHIFT=COUNTER_TRIM/2
COUNTER_LEFT_OFFSET=.65+COUNTER_TRIM
ENTRY_LANTERN_HEIGHT=2.47
ENTRY_LANTERN_SCALE=.78


def staff_entry_plan(idx,w,dep):
    x=-w/2+.60;y=dep/2
    if idx==2:
        # Bend between the fixed front post and the fixed first guest stool.
        path=[(0,y-1.20),(x,y-1.20),(x,y-.80),(x,y+.16),(-w/2+.49,y+.32),
              (-w/2+.35,y+.47),(-w/2+.30,y+.75),(-w/2+.30,y+1.35)]
    else:path=[(0,y-1.20),(x,y-1.20),(x,y-.80),(x,y+.15),(-w/2+.50,y+.45),(-w/2+.45,y+.75),(-w/2+.45,y+1.35)]
    return dict(shop=f'S{idx+1:02d}',side=-1,centerline=path,
                counter_left=-w/2+COUNTER_LEFT_OFFSET,counter_right=w/2-.65,
                clear_width=COUNTER_LEFT_OFFSET-.215,headroom=2.2,
                target_radius=.325,post_and_floor_unchanged=True)
