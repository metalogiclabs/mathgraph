"""Human-authored finite fixtures: complete authoritative tables for bounded tests.

Protected property is the hidden bit, and the original observation is the record bit.
No empirical or source-specific interpretation is inferred from these fixtures.
"""


def bit_model(grants=None, desired=None):
    return {
        'name': 'hidden-record-four-state', 'protected': [0, 0, 1, 1],
        'readouts': [{'name':'read_r','values':[0,1,0,1],'cost':1}],
        'operations': [
            {'name':'flip_r','image':[1,0,3,2],'cost':1},
            {'name':'zero_r','image':[0,0,2,2],'cost':1},
            {'name':'couple_h_xor_r','image':[0,1,3,2],'cost':3},
            {'name':'destroy_h','image':[0,0,1,1],'cost':1},
        ],
        'grants': list(grants if grants is not None else {'flip_r','zero_r','couple_h_xor_r','destroy_h','read_r'}),
        'base_readouts': ['read_r'],
        'desired_labels': list(desired if desired is not None else (0,1,2,3)),
    }


def cyclic_model(grants=None, desired=None):
    """Independent three-state fixture to test same compiler on different state cardinality."""
    return {
        'name':'three-state-output-control', 'protected':[0,1,0],
        'readouts':[{'name':'read_visible','values':[0,0,1],'cost':2}],
        'operations':[
            {'name':'swap_equal_protected','image':[2,1,0],'cost':2},
            {'name':'reset_visible','image':[0,1,0],'cost':1},
            {'name':'unsafe_merge','image':[1,1,1],'cost':1},
        ],
        'grants':list(grants if grants is not None else {'swap_equal_protected','reset_visible','unsafe_merge','read_visible'}),
        'base_readouts':['read_visible'],
        'desired_labels': list(desired if desired is not None else (0,1,2)),
    }