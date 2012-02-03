
from aql_logging import logInfo,logWarning
from aql_utils import equalFunctionArgs
from aql_errors import InvalidHandlerMethodArgs,InvalidHandlerNoMethod

#//===========================================================================//

_events = set()

def   _event( event_method ):
  _events.add( event_method )

#//-------------------------------------------------------//
def   verifyHandler( handler ):
  if type(handler) is not EventHandler:
    for event_method in _events:
      try:
        event_method_name = event_method.__name__
        
        handler_method = getattr( handler, event_method_name )
        
        if not equalFunctionArgs( event_method, handler_method ):
          raise InvalidHandlerMethodArgs( event_method_name )
      
      except AttributeError:
        raise InvalidHandlerNoMethod( event_method_name )
  
#//===========================================================================//

class EventHandler( object ):
  
  #//-------------------------------------------------------//
  @_event
  def   dataFileIsNotSync( self, filename ):
    """
    Inconsistency state of Data file. Either internal error or external corruption.
    """
    logWarning("Internal error: DataFile is unsynchronized")
  
  #//-------------------------------------------------------//
  @_event
  def   depValueIsCyclic( self, value ):
    logWarning("Internal error: Cyclic dependency value: %s" % value )
  
  #//-------------------------------------------------------//
  @_event
  def   unknownValue( self, value ):
    logWarning("Internal error: Unknown value: %s " % value )
  
  
  #//-------------------------------------------------------//
  
  @_event
  def   outdatedNode( self, node ):
    """
    Node needs to be rebuilt.
    """
    logInfo("Outdated node: %s" % node )
  
  #//-------------------------------------------------------//
  
  @_event
  def   targetIsBuiltTwiceByNodes( self, value, node1, node2 ):
    logWarning("Target '%s' is built by different nodes: '%s', '%s' " % ( value.name, node1, node2 ) )
  
  #//-------------------------------------------------------//
