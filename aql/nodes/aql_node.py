
# Copyright (c) 2011-2014 The developers of Aqualid project - http://aqualid.googlecode.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom
# the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
# AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__all__ = (
  'Node', 'BatchNode',
)

import os

from aql.utils import simpleObjectSignature, dumpSimpleObject, newHash, Chdir
from aql.util_types import toSequence, isString, toString, FilePath, AqlException

from aql.values import ValueBase, FileValueBase, pickleable

#//===========================================================================//

class   ErrorNodeDependencyInvalid( AqlException ):
  def   __init__( self, dep ):
    msg = "Invalid node dependency: %s" % (dep,)
    super(ErrorNodeDependencyInvalid, self).__init__( msg )
    
class   ErrorNoTargets( AqlException ):
  def   __init__( self, node ):
    msg = "Node targets are not built or set yet: %s" % (node.getBuildStr( brief = False ),)
    super(ErrorNoTargets, self).__init__( msg )

class   ErrorNoSrcTargets( AqlException ):
  def   __init__( self, node, src_value ):
    msg = "Source '%s' targets are not built or set yet: %s" % (src_value.get(), node.getBuildStr( brief = False ),)
    super(ErrorNoSrcTargets, self).__init__( msg )

class   ErrorUnactualValue( AqlException ):
  def   __init__( self, value ):
    msg = "Target value is not actual: %s (%s)" % (value.name, type(value))
    super(ErrorUnactualValue, self).__init__( msg )

class   ErrorNoImplicitDeps( AqlException ):
  def   __init__( self, node ):
    msg = "Node implicit dependencies are not built or set yet: %s" % (node.getBuildStr( brief = False ),)
    super(ErrorNoImplicitDeps, self).__init__( msg )

class   ErrorNodeNotInitialized( AqlException ):
  def   __init__( self, node ):
    msg = "Node is not initialized yet: %s" % (node, )
    super(ErrorNodeNotInitialized, self).__init__( msg )

class   ErrorNodeUnknownSource( AqlException ):
  def   __init__( self, src_value ):
    msg = "Unknown source value: %s (%s)" % (src_value, type(src_value))
    super(ErrorNodeUnknownSource, self).__init__( msg )

#//===========================================================================//

def   _actualDeps( vfile, dep_keys ):
  if dep_keys:
    values = vfile.getValues( dep_keys )
    
    if values is None:
      # if __debug__:
      #   print( "ideps are None")
      return False
    
    for key, value in zip(dep_keys, values):
      if not value:
        # if __debug__:
        #   print( "idep '%s' is false" % (value,))
        return False
      
      actual_value = value.getActual()
      if value != actual_value:
        # if __debug__:
        #   print( "idep '%s' changed to '%s'" % (value, actual_value))
        vfile.replaceValue( key, actual_value )
        return False
  
  return True

#//===========================================================================//

def   _actualValues( values ):
  if values is None:
    return False
  
  for value in values:
    if not value.isActual():
      return False
      
  return True

#//===========================================================================//

def   _makeValues( value_maker, values, use_cache ):
  return tuple( value_maker( value, use_cache = use_cache ) for value in toSequence(values) )

#//===========================================================================//

def   _ensureActualValues( values ):
  for value in values:
    if not value.isActual():
      raise ErrorUnactualValue( value )

#//===========================================================================//

def   _getTraceArg( value, brief ):
  if isinstance( value, FileValueBase ):
    value = value.get()
    if brief:
      value = os.path.basename( value )
  else:
    if isinstance( value, ValueBase ):
      value = value.get()

    if isinstance( value, FilePath ):
      if brief:
        value = os.path.basename( value )

    elif isString( value ):
      value = value.strip()

      npos = value.find('\n')
      if npos != -1:
        value = value[:npos]

      max_len = 64 if brief else 256
      src_len = len(value)
      if src_len > max_len:
        value = "%s..." % value[:max_len]

    else:
      value = None
  
  return value

#//===========================================================================//

def   _joinArgs( values, brief ):
  
  args = []
  
  for arg in toSequence(values):
    arg = _getTraceArg(arg, brief )
    if arg:
      args.append( arg )
  
  if not brief or (len(args) < 3):
    return ' '.join( args )
  
  wish_size = 128
  
  args_str = [ args.pop(0) ]
  last = args.pop()
  
  size = len(args_str[0]) + len(last)
  
  for arg in args:
    size += len(arg)
    
    if size > wish_size:
      args_str.append('...')
      break
    
    args_str.append( arg )
    
  args_str.append( last )
  
  return ' '.join( args_str )

#//===========================================================================//

def   _getBuildStr( args, brief ):
    
    args = iter(args)
    
    name    = next(args, None)
    sources = next(args, None)
    targets = next(args, None)
    
    name    = _joinArgs( name,    brief )
    sources = _joinArgs( sources, brief )
    targets = _joinArgs( targets, brief )
    
    build_str  = name
    if sources:
      build_str += " << " + sources
    if targets:
      build_str += " >> " + targets
    
    return build_str
  
#//===========================================================================//
  
def   _getClearStr( args, brief = True ):
  
  args    = iter(args)
  next(args, None ) # name
  next(args, None ) # sources
  targets = next(args, None )
  
  return _joinArgs( targets, brief )

#//===========================================================================//

@pickleable
class   NodeValue (ValueBase):
  
  __slots__ = (
    'targets',
    'itargets',
    'idep_keys',
  )
  
  #//-------------------------------------------------------//
  
  def   __new__( cls, name, signature = None, targets = None, itargets = None, idep_keys = None ):
    
    self = super(NodeValue,cls).__new__(cls, name, signature )
    
    self.targets    = targets
    self.itargets   = itargets
    self.idep_keys  = idep_keys
    
    return self
  
  #//-------------------------------------------------------//
  
  def   __eq__( self, other):
    return (type(self) == type(other)) and (self.__getnewargs__() == other.__getnewargs__())
  
  #//-------------------------------------------------------//
  
  def   get(self):
    return self.name
  
  #//-------------------------------------------------------//
  
  def     __getnewargs__(self):
    return self.name, self.signature, self.targets, self.itargets, self.idep_keys
  
  #//-------------------------------------------------------//
  
  def   __bool__( self ):
    return (self.signature is not None) and (self.targets is not None)
  
  #//-------------------------------------------------------//
  
  def   actual( self, vfile ):
    if not self.signature:
      # if __debug__:
      #   print( "No signature.")
      return False
    
    other = vfile.findValue( self )
    
    if other is None:
      # if __debug__:
      #   print( "Previous value '%s' has not been found." % (self.name,))
      return False
    
    if self.signature != other.signature:
      # if __debug__:
      #   print( "Sources signature is changed: %s - %s" % (self.signature, other.signature) )
      return False
    
    targets   = other.targets
    itargets  = other.itargets
    idep_keys = other.idep_keys
    
    if not _actualDeps( vfile, idep_keys ):
      # if __debug__:
      #   print( "ideps are not actual: %s" % (self.name,))
      return False
    
    if not _actualValues( targets ):
      # if __debug__:
      #   print( "targets are not actual: %s" % (self.name,))
      return False
    
    self.targets = targets
    self.itargets = itargets
    
    return True

  #//-------------------------------------------------------//

#//===========================================================================//

#noinspection PyAttributeOutsideInit
class Node (object):
  
  __slots__ = \
  (
    'builder',
    'builder_data',
    'options',
    'cwd',
    
    'name',
    'signature',
    
    'sources',
    'source_values',
    
    'dep_nodes',
    'dep_values',
    
    'targets',
    'itargets',
    'ideps',
  )
  
  #//-------------------------------------------------------//

  def   __init__( self, builder, sources, cwd = None ):

    self.builder = builder
    self.options = getattr( builder, 'options', None )
    self.builder_data = None
    
    if cwd is None:
      self.cwd = os.path.abspath( os.getcwd() )
    else:
      self.cwd = cwd
    
    self.sources = toSequence( sources )
    self.dep_nodes = set()
    self.dep_values = []
  
  #//=======================================================//
  
  def   isBatch(self):
    return False
  
  #//=======================================================//
  
  def   copy( self, sources, builder = None ):
    other = object.__new__( self.__class__ )
    
    other.builder       = builder if builder else self.builder
    other.options       = self.options
    other.builder_data  = None
    other.cwd           = self.cwd
    other.sources       = toSequence( sources )
    other.dep_nodes     = self.dep_nodes
    other.dep_values    = self.dep_values
    
    return other
  
  #//=======================================================//

  def   __getattr__(self, attr):
    if attr == 'name':
      return self._setName()

    if attr == 'signature':
      return self._setSignature()

    if attr == 'source_values':
      return self._setSourceValues()

    if attr in ['targets', 'itargets', 'ideps' ]:
      raise ErrorNoTargets( self )

    raise AttributeError( "Node has not attribute '%s'" % (attr,) )

  #//=======================================================//
  
  def   getNames(self):
    return (self.name,)
  
  #//=======================================================//

  def   depends( self, dependencies ):
    
    dep_nodes = self.dep_nodes
    dep_values = self.dep_values
    
    for value in toSequence( dependencies ):
      if isinstance( value, Node ):
        dep_nodes.add( value )
      
      elif isinstance( value, ValueBase ):
        dep_values.append( value )
      
      else:
        raise ErrorNodeDependencyInvalid( value )
    
    dep_values.sort( key = lambda v: v.name )
  
  #//=======================================================//
  
  def   getDepNodes(self):
    return self.dep_nodes
  
  #//=======================================================//
  
  def   updateDepValues(self):
    dep_nodes = self.dep_nodes
    
    if not dep_nodes:
      return
    
    dep_values = self.dep_values
    
    for node in dep_nodes:
      dep_values += node.targets
    
    dep_nodes.clear()
    dep_values.sort( key = lambda v: toString( v.name ) )
  
  #//=======================================================//
  
  def   getDepValues(self):
    self.updateDepValues()
    return self.dep_values
  
  #//=======================================================//
  
  def   initiate(self):
    with Chdir(self.cwd):
      self.builder = self.builder.initiate()

  #//=======================================================//
  
  def   _getNameHash( self ):
    return newHash( dumpSimpleObject( self.builder.name ) )
  
  #//=======================================================//
  
  def   _getSignatureHash( self ):
    
    sign  = [ self.builder.signature ]
    
    for value in self.getDepValues():
      if value:
        sign.append( value.name )
        sign.append( value.signature )
      else:
        return None
    
    sign_hash = newHash( dumpSimpleObject( sign ) )

    return sign_hash
  
  #//=======================================================//
  
  def   _setName( self ):
    
    targets = self.builder.getTargetValues( self )
    if targets:
      self.targets = toSequence( targets )
      names = sorted( value.valueId() for value in targets )
      name = simpleObjectSignature( names )
    else:
      name_hash = self._getNameHash()
      source_names = sorted( value.name for value in self.getSourceValues() )
      for source_name in source_names:
        name_hash.update( dumpSimpleObject( source_name ) )
      name = name_hash.digest()
    
    self.name = name
    return name

  #//=======================================================//
  
  def   _setSignature( self ):
    
    sign_hash = self._getSignatureHash()
    
    if sign_hash is None:
      sign = None
    else:
      for value in self.getSourceValues():
        sign_hash.update( dumpSimpleObject( value.signature ) )
      sign = sign_hash.digest()
    
    self.signature = sign
    return sign
  
  #//=======================================================//
  
  def   _setSourceValues(self):
    values = []
    
    makeValue = self.builder.makeValue
    
    with Chdir(self.cwd):
      for src in self.sources:
        
        if isinstance( src, Node ):
          values += src.targets
        
        elif isinstance( src, ValueBase ):
          values.append( src )
        
        else:
          value = makeValue( src, use_cache = True )
          values.append( value )

    values = tuple(values)
    self.source_values = values
    return values
  
  #//=======================================================//
  
  def   getSources(self):
    return tuple( src.get() for src in self.getSourceValues() )
  
  #//=======================================================//
  
  def   getSourceValues(self):
    return self.source_values
  
  #//=======================================================//
  
  def   getSourceNodes(self):
    return tuple( node for node in self.sources if isinstance(node,Node) )
  
  #//=======================================================//
  
  def   shrink(self):
    self.cwd = None
    self.dep_nodes = None
    self.dep_values = None
    self.sources = None
    self.source_values = None
    
    self.name = None
    self.signature = None
    self.builder = None
    self.builder_data = None
    self.options = None
  
  #//=======================================================//
  
  def   isBuilt(self):
    return self.builder is None
  
  #//=======================================================//
  
  def   build(self):
    output = self.builder.build( self )

    if getattr(self, 'targets', None) is None:
      raise ErrorNoTargets( self )
    
    return output
  
  #//=======================================================//
  
  def   buildDepends( self ):
    return self.builder.depends( self )
  
  #//=======================================================//
  
  def   buildReplace( self ):
    
    sources = self.builder.replace( self )
    if sources is None:
      return False
    
    self.sources = sources
    del self.source_values
    
    return True
  
  #//=======================================================//
  
  def   buildSplit( self ):
    self.updateDepValues()
    return self.builder.split( self )
  
  #//=======================================================//
  
  def   save( self, vfile ):
    if __debug__:
      _ensureActualValues( self.targets )
      _ensureActualValues( self.ideps )

    idep_keys = vfile.addValues( self.ideps )
    
    node_value = NodeValue( name = self.name, signature = self.signature,
                            targets = self.targets, itargets = self.itargets, idep_keys = idep_keys )
    
    vfile.addValue( node_value )

  #//=======================================================//
  
  def   clear( self, vfile ):
    """
    Cleans produced values
    """
    node_value = NodeValue( name = self.name )
    
    node_value = vfile.findValue( node_value )
    if node_value:
      targets = node_value.targets
      itargets = node_value.itargets
      
      if targets is not None:
        self.targets  = targets
        self.itargets = itargets
      else:
        self.targets  = tuple()
        self.itargets = tuple()

    vfile.removeValues( [ node_value ] )
    
    try:
      self.builder.clear( self )
    except Exception:
      pass
    
  #//=======================================================//
  
  def   isActual( self, vfile, built_node_names = None ):
    node_value = NodeValue( name = self.name, signature = self.signature )
    
    if not node_value.actual( vfile ) or ((built_node_names is not None) and (node_value.name not in built_node_names)):
      return False
    
    self.targets  = node_value.targets
    self.itargets = node_value.itargets
    return True
    
  #//=======================================================//
  
  def   setTargets( self, targets, itargets = None, ideps = None, value_maker = None ):

    if value_maker is None:
      value_maker = self.builder.makeValue
    
    self.targets  = _makeValues( value_maker, targets,   use_cache = False )
    self.itargets = _makeValues( value_maker, itargets,  use_cache = False )
    self.ideps    = _makeValues( value_maker, ideps,     use_cache = True )

  #//=======================================================//
  
  def   setFileTargets( self, targets, itargets = None, ideps = None ):
    self.setTargets( targets = targets, itargets = itargets, ideps = ideps,
                     value_maker = self.builder.makeFileValue )
  
  #//=======================================================//
  
  def   setNoTargets( self ):
    self.setTargets( targets = None )
  
  #//=======================================================//
  
  def   get(self):
    return self.getTargets()
  
  #//=======================================================//
  
  def   getTargets(self):
    return tuple( target.get() for target in self.getTargetValues() )
  
  #//=======================================================//
  
  def   getTargetValues(self):
    return self.targets
  
  #//=======================================================//
  
  def   getBuildTargetValues(self):
    return self.targets
  
  #//=======================================================//

  def   getSideEffectValues(self):
    return self.itargets
  
  #//=======================================================//
  
  def   removeTargets(self):
    for value in self.getTargetValues():
      value.remove()
    
    for value in self.getSideEffectValues():
      value.remove()
  
  #//=======================================================//
  
  def   getBuildStr( self, brief = True ):
    args = self.builder.getBuildStrArgs( self, brief = brief )
    return _getBuildStr( args, brief )
  
  #//=======================================================//
  
  def   getClearStr( self, brief = True ):
    args = self.builder.getBuildStrArgs( self, brief = brief )
    return _getClearStr( args, brief )

#//===========================================================================//

#noinspection PyAttributeOutsideInit
class BatchNode (Node):
  
  __slots__ = \
    (
      'node_values',
      'changed_source_values',
    )
  
  #//=======================================================//
  
  def   isBatch(self):
    return True
  
  #//=======================================================//
  
  def   getNames(self):
    return tuple(value.name for value, ideps in self.node_values.values())
  
  #//=======================================================//
  
  def   __getattr__(self, attr):
    if attr in ['name', 'signature']:
      raise AttributeError("Attribute '%s' is not applicable for BatchNode" % (attr,))

    if attr == 'node_values':
      return self._setNodeValues()

    if attr == 'changed_source_values':
      return self._setSourceValues()

    return super(BatchNode,self).__getattr__( attr )

  #//=======================================================//

  def   _setNodeValues( self ):

    name_hash = self._getNameHash()
    sign_hash = self._getSignatureHash()
    
    node_values = {}
    
    for src_value in self.source_values:
      name = simpleObjectSignature( src_value.name, name_hash )
      
      if sign_hash and src_value.signature:
        signature = simpleObjectSignature( src_value.signature, sign_hash )
      else:
        signature = None
      
      ideps = []
      node_values[ src_value ] = NodeValue( name, signature ), ideps
    
    self.node_values = node_values
    return node_values
      
  #//=======================================================//
  
  def   _setSourceValues(self):
    src_values = super(BatchNode,self)._setSourceValues()
    self.changed_source_values = src_values
    return src_values
  
  #//=======================================================//
  
  def   getSourceValues(self):
    return self.changed_source_values
  
  #//=======================================================//
  
  def   save( self, vfile ):
    
    for src_value in self.changed_source_values:
      node_value, ideps = self.node_values[ src_value ]

      if __debug__:
        if node_value.targets is None:
          raise ErrorNoTargets( self )

        _ensureActualValues( node_value.targets )
        _ensureActualValues( ideps )

      node_value.idep_keys = vfile.addValues( ideps )
      
      # if __debug__:
      #   print("save node value: %s" % (node_value.name))
      
      vfile.addValue( node_value )
  
  #//=======================================================//
  
  def   clear( self, vfile ):
    targets = []
    itargets = []
    node_values = []
    
    for src_value in self.source_values:
      node_value, ideps = self.node_values[ src_value ]
      
      node_value = vfile.findValue( node_value )
      
      if node_value:
        node_values.append( node_value )
        
        if node_value.targets is not None:
          targets   += node_value.targets
          itargets  += node_value.itargets
              
    self.targets  = targets
    self.itargets = itargets
    
    vfile.removeValues( node_values )
    
    try:
      self.builder.clear( self )
    except Exception:
      pass
  
  #//=======================================================//
  
  def   build(self):
    output = self.builder.buildBatch( self )
    self.__populateTargets()
    
    return output
  
  #//=======================================================//
  
  def   __populateTargets( self ):
    targets   = []
    itargets  = []
    
    for src_value in self.source_values:
      node_value, ideps = self.node_values[ src_value ]
      node_targets = node_value.targets
      if node_targets is None:
        raise ErrorNoSrcTargets( self, src_value )
      
      targets += node_targets
      itargets += node_value.itargets
    
    self.targets = tuple(targets)
    self.itargets = tuple(itargets)
  
  #//=======================================================//
  
  def   isActual( self, vfile, built_node_names = None ):
    
    changed_sources = []
    targets = []
    itargets = []
    
    for src_value in self.source_values:
      node_value, ideps = self.node_values[ src_value ]
      
      if not node_value.actual( vfile ) or ((built_node_names is not None) and (node_value.name not in built_node_names)):
        changed_sources.append( src_value )
      else:
        targets   += node_value.targets
        itargets  += node_value.itargets
    
    if changed_sources:
      self.changed_source_values = changed_sources
      return False
    
    self.targets  = targets
    self.itargets = itargets
    return True
  
  #//=======================================================//
  
  def   setTargets( self, targets, itargets = None, ideps = None, value_maker = None ):
    raise Exception( "setTargets() is not allowed for batch build." )
  
  #//=======================================================//
  
  def   split( self, builder ):
    raise Exception( "split() is not allowed for batch build." )
  
  #//=======================================================//
  
  def   setSourceTargets( self, src_value, targets, itargets = None, ideps = None, value_maker = None ):
    
    if value_maker is None:
      value_maker = self.builder.makeValue
    
    try:
      node_value, node_ideps = self.node_values[ src_value ]
    except KeyError:
      raise ErrorNodeUnknownSource( src_value )
    
    node_value.targets  = _makeValues( value_maker, targets,  use_cache = False )
    node_value.itargets = _makeValues( value_maker, itargets, use_cache = False )
    ideps               = _makeValues( value_maker, ideps,    use_cache = True )
    
    node_ideps[:] = ideps
    
  #//=======================================================//
  
  def   setNoTargets( self ):
    for src_value in self.changed_source_values:
      node_value, node_ideps = self.node_values[ src_value ]
      node_value.targets = tuple()
      node_value.itargets = tuple()
  
  #//=======================================================//
  
  def   setSourceFileTargets( self, src_value, targets, itargets = None, ideps = None ):
    self.setSourceTargets( src_value, targets = targets, itargets = itargets, ideps = ideps,
                     value_maker = self.builder.makeFileValue )
  
  #//=======================================================//
  
  def   getBuildTargetValues(self):
    targets = []
    
    for src_value in self.changed_source_values:
      node_value, ideps = self.node_values[ src_value ]
      node_targets = node_value.targets
      if node_targets:
        targets += node_targets
    
    return targets
  
  #//=======================================================//
  
  def   shrink(self):
    super( BatchNode, self).shrink()
    
    self.node_values = None
    self.changed_source_values = None

  #//=======================================================//
  
  def   getBuildStr( self, brief = True ):
    args = self.builder.getBuildStrArgs( self, brief = brief )
    return _getBuildStr( args, brief )
  
  #//=======================================================//
  
  def   getClearStr( self, brief = True ):
    args = self.builder.getBuildStrArgs( self, brief = brief )
    return _getClearStr( args, brief )
