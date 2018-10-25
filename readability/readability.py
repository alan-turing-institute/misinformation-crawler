__all__ = ['readability']

# Don't look below, you will not understand this Python code :) I don't.

from js2py.pyjs import *
# setting scope
var = Scope( JS_BUILTINS )
set_global_object(var)

# Code follows:
var.registers(['readabilityPath', 'fs', 'JSDOM', 'scopeContext', 'simplify_html', 'path', 'jsdomPath', 'url', 'vm'])
@Js
def PyJsHoisted_simplify_html_(article_html, this, arguments, var=var):
    var = Scope({'article_html':article_html, 'this':this, 'arguments':arguments}, var)
    var.registers(['simple_html', 'doc', 'article_html'])
    var.put('doc', var.get('scopeContext').get('JSDOM').create(var.get('html')).get('window').get('document'))
    var.put('simple_html', var.get('scopeContext').get('Readability').create(var.get('doc')).callprop('parse'))
    return var.get('simple_html')
PyJsHoisted_simplify_html_.func_name = 'simplify_html'
var.put('simplify_html', PyJsHoisted_simplify_html_)
var.put('path', var.get('require')(Js('path')))
var.put('fs', var.get('require')(Js('fs')))
var.put('url', var.get('require')(Js('url')))
var.put('vm', var.get('require')(Js('vm')))
var.put('readabilityPath', var.get('path').callprop('join', var.get('__dirname'), Js('Readability.js')))
var.put('jsdomPath', var.get('path').callprop('join', var.get('__dirname'), Js('JSDOMParser.js')))
var.put('JSDOM', var.get('require')(Js('jsdom')).get('JSDOM'))
PyJs_Object_0_ = Js({})
var.put('scopeContext', PyJs_Object_0_)
var.get('scopeContext').put('dump', var.get('console').get('log'))
var.get('scopeContext').put('console', var.get('console'))
var.get('scopeContext').put('URL', var.get('url').get('URL'))
var.get('scopeContext').put('JSDOM', var.get('JSDOM'))
var.get('vm').callprop('runInNewContext', var.get('fs').callprop('readFileSync', var.get('readabilityPath')), var.get('scopeContext'), var.get('readabilityPath'))
pass
PyJs_Object_1_ = Js({'simplify_html':var.get('scopeContext').get('simplify_html')})
var.get('module').put('exports', PyJs_Object_1_)
pass


# Add lib to the module scope
readability = var.to_python()