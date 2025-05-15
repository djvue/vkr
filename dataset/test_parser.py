import pytest
import aiopath
from dataset.parser import end_of_block, parse_imports, parse_funcs, parse_directives, calculate_deps


@pytest.mark.parametrize('code, start, block',
    [
("""
var a, b, c map[string][]struct{
    a int
    b int
}
""", 13, """map[string][]struct{
    a int
    b int
}"""),
("""
var a, b, c map[string][]interface{
    a() int
    b() struct {
        c int
    }
}
""", 13, """map[string][]interface{
    a() int
    b() struct {
        c int
    }
}"""),
("""
func myfn(x int) (x, y error) {
    var a, b, c map[string][]interface{
        a() int
        b() struct {
            c int
        }
    }
 
    return []string{`
    asdf}
    ]
    )
    `}
}
""", 31, """{
    var a, b, c map[string][]interface{
        a() int
        b() struct {
            c int
        }
    }
 
    return []string{`
    asdf}
    ]
    )
    `}
}"""),
    ])
def test_end_of_block(code: str, start: int, block: str):
    end = end_of_block(code, start)
    

    assert code[start:end] == block


@pytest.mark.parametrize('code, expected',
    [
("""
import (
    "os"
    "net" // my-comment 1
    . "bytes"
    . "bytes2" // my-comment 3
    _ "github.com/some-author/some-package4"
    _ "github.com/some-author/some-package5" // my-comment 5
    myalias6 "github.com/some-author/some-package6"
    myalias7 "github.com/some-author/some-package7" // my-comment 7
    "github.com/some-author/some-package8"
    "github.com/some-author/some-package9" // my-comment 9
    "github.com/some-author/_package10"
    "github.com/some-author/_package11" // my-comment 11
)
 
import "os12"
import "net13" // my-comment 13
import . "bytes14"
import . "bytes15" // my-comment 15
import _ "github.com/some-author/some-package16"
import _ "github.com/some-author/some-package17" // my-comment 17
import myalias18 "github.com/some-author/some-package18"
import myalias19 "github.com/some-author/some-package19" // my-comment 19
import "github.com/some-author/some-package20"
import "github.com/some-author/some-package21" // my-comment 21
import "github.com/some-author/_package22"
import "github.com/some-author/_package23" // my-comment 23
""", {
    "os12": ["os12"],
    "net13": ["net13"],
    "myalias18": ["github.com/some-author/some-package18"],
    "myalias19": ["github.com/some-author/some-package19"],
    "package20": ["github.com/some-author/some-package20"],
    "package21": ["github.com/some-author/some-package21"],
    "_package22": ["github.com/some-author/_package22"],
    "_package23": ["github.com/some-author/_package23"],
    "os": ["os"],
    "net": ["net"],
    ".": ["bytes14", "bytes15", "bytes", "bytes2"],
    "_": ["github.com/some-author/some-package16", "github.com/some-author/some-package17", "github.com/some-author/some-package4", "github.com/some-author/some-package5"],
    "myalias6": ["github.com/some-author/some-package6"],
    "myalias7": ["github.com/some-author/some-package7"],
    "package8": ["github.com/some-author/some-package8"],
    "package9": ["github.com/some-author/some-package9"],
    "_package10": ["github.com/some-author/_package10"],
    "_package11": ["github.com/some-author/_package11"],
}),
    ])
def test_parse_imports(code: str, expected: dict[str, list[str]]):
    res = parse_imports(code)
    

    assert res == expected


@pytest.mark.parametrize('code, expected',
    [
("""
package asdf

import "os12"
 
func myfn(x int) (x, y error) {
    var a, b, c map[string][]interface{
        a() int
        b() struct {
            c int
        }
    }
 
    return []string{`
    asdf}
    ]
    )
    `}
}
 
func ptrTo[T ~int|~int32|~int64|float](x T) *T { return &x }
""", {'myfn': """func myfn(x int) (x, y error) {
    var a, b, c map[string][]interface{
        a() int
        b() struct {
            c int
        }
    }
 
    return []string{`
    asdf}
    ]
    )
    `}
}""",
'ptrTo': 'func ptrTo[T ~int|~int32|~int64|float](x T) *T { return &x }'
}),
    ])
def test_parse_funcs(code: str, expected: dict[str, str]):
    res = parse_funcs(code)
    

    assert res == expected


@pytest.mark.parametrize('code, expected',
    [
("""
package asdf

import "os12"
 
type T1 struct {
    a struct {
        b int
    }
}
 
type (
    T2 interface {
        do() int
        do2() interface {
            do() int
        }
    }
    T3 int
)
 
type T4 string
type t5_ = error
 
var v1 = 1
var v2 int = 10
var v3, v4 string = "v3", "v4"
var v5, v6 float
var v7, v8 = 7, 8
var v9 struct{
    a int
} = struct{
    a int
}{
    a: 9
}
var v10 interface{
    do()
}
var v11 = map[string]int{
    "v11": 11,
}
 
var (
    v21 = 21
    v22 int = 10
    v23, v24 string = "v3", "v4"
    v25, v26 float
    v27, v28 = 7, 8
    v29 struct{
        a int
    } = struct{
        a int
    }{
        a: 9
    }
    v30 interface{
        do()
    }
    v31 = map[string]int{
        "v31": 31,
    }
)
 
const c1 = 1
const c2 int = 3
const c3, c4 string = "c3", "c4"
const c5, c6 = 5, c2
 
const (
    c21 = 1
    c22 int = 3
    c23, c24 string = "c23 = 23", "c24"
    c25, c26 = 5, c22
)
 
func ptrTo[T ~int|~int32|~int64|float](x T) *T { return &x }
""", {
    'type': {
'T1': """T1 struct {
    a struct {
        b int
    }
}""",
'T2': """T2 interface {
        do() int
        do2() interface {
            do() int
        }
    }""",
'T3': 'T3 int',
'T4': 'T4 string',
't5_': 't5_ = error'
    },

    'var': {
'v1': 'v1 = 1',
'v2': 'v2 int = 10',
'v3': 'v3 string = "v3"',
'v4': 'v4 string = "v4"',
'v5': 'v5 float',
'v6': 'v6 float',
'v7': 'v7 = 7',
'v8': 'v8 = 8',
'v9': """v9 struct{
    a int
} = struct{
    a int
}{
    a: 9
}""",
'v10': """v10 interface{
    do()
}""",
'v11': """v11 = map[string]int{
    "v11": 11,
}""",
'v21': 'v21 = 21',
'v22': 'v22 int = 10',
'v23': 'v23 string = "v3"',
'v24': 'v24 string = "v4"',
'v25': 'v25 float',
'v26': 'v26 float',
'v27': 'v27 = 7',
'v28': 'v28 = 8',
'v29': """v29 struct{
        a int
    } = struct{
        a int
    }{
        a: 9
    }""",
'v30': """v30 interface{
        do()
    }""",
'v31': """v31 = map[string]int{
        "v31": 31,
    }""",
    },
    'const': {
'c1': 'c1 = 1',
'c2': 'c2 int = 3',
'c3': 'c3 string = "c3"',
'c4': 'c4 string = "c4"',
'c5': 'c5 = 5',
'c6': 'c6 = c2',
'c21': 'c21 = 1',
'c22': 'c22 int = 3',
'c23': 'c23 string = "c23 = 23"',
'c24': 'c24 string = "c24"',
'c25': 'c25 = 5',
'c26': 'c26 = c22',
    },
}),
    ])
def test_parse_directives(code: str, expected: dict[str, dict[str, str]]):
    res = parse_directives(code)
    

    assert res == expected

@pytest.mark.parametrize('func_body, directives, imports, expected',
    [
(
    {
        'fn_a': 'fn_a,type_a,var_a,const_b,import_b',
        'fn_b': 'b,fn_a',
    },
    {
        'type': {
            'type_a': 'type_a,a',
            'type_b': 'const_b,import_b',
        },
        'var': {
            'var_a': 'type_a,const_a,const_b,fn_a',
            'var_b': 'b,import_b,var_a',
        },
        'const': {
            'const_a': '10',
            'const_b': 'const_a',
        },
    },
    {
        '.': ['dot'],
        '_': ['underscore'],
        'import_a': ['import_a'],
        'import_b': ['import_b'],
    },
    {
        ('func', 'fn_a'): set({
            ('type', 'type_a'),
            ('var', 'var_a'),
            ('const', 'const_b'),
            ('import', 'import_b'),
            ('import', '.'),
            ('import', '_'),
        }),
        ('func', 'fn_b'): set({
            ('func', 'fn_a'),
            ('import', '.'),
            ('import', '_'),
        }),
        ('type', 'type_a'): set({
            ('import', '.'),
            ('import', '_'),
        }),
        ('type', 'type_b'): set({
            ('const', 'const_b'),
            ('import', 'import_b'),
            ('import', '.'),
            ('import', '_'),
        }),
        ('var', 'var_a'): set({
            ('type', 'type_a'),
            ('const', 'const_a'),
            ('const', 'const_b'),
            ('func', 'fn_a'),
            ('import', '.'),
            ('import', '_'),
        }),
        ('var', 'var_b'): set({
            ('var', 'var_a'),
            ('import', 'import_b'),
            ('import', '.'),
            ('import', '_'),
        }),
        ('const', 'const_a'): set({
            ('import', '.'),
            ('import', '_'),
        }),
        ('const', 'const_b'): set({
            ('const', 'const_a'),
            ('import', '.'),
            ('import', '_'),
        }),
        ('import', '.'): set({}),
        ('import', '_'): set({}),
        ('import', 'import_a'): set({}),
        ('import', 'import_b'): set({}),
    },
),
    ])
def test_calculate_deps(func_body: dict[str, str], directives: dict[str, dict[str, str]], imports: dict[str, list[tuple[str, str]]], expected: dict[str, dict[str, dict[str, set[str]]]]):
    res = calculate_deps(func_body, directives, imports)
    

    assert res == expected
