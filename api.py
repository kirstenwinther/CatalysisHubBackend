"""
API for GraphQL enhanced queries against catapp and ase-db database

Some Examples:

- Get total number of rows in table (in this case reactions):
    {reactions (first: 0) {
      totalCount
    }}

- Filter by reactants and products from reactions:
    {reactions(reactants: "OH", products: "H2O") {
      edges {
        node {
          Reaction
          reactionEnergy
          activationEnergy
        }
      }
    }}

- Filter by several reactants or products from reactions:
    {reactions(reactants: "COstar+NOstar") {
      edges {
        node {
          Reaction
          reactionEnergy
          activationEnergy
        }
      }
    }}

- Author-name from publications:
    {publications(authors: "~Bajdich") {
      edges {
        node {
          reactions {
            chemicalComposition
            Reaction
            reactionEnergy
           }	
         }
        }
      }}

- Full text search in reactions (title, authors, year, reactants and products): ### Doesn't work!
    {reactions(search: "oxygen evolution bajdich 2017 OOH") {
      edges {
        node {
          Reaction
          PublicationTitle
          PublicationAuthors
          year
        }
      }
    }}

- Full text search in publications (title, authors, year): 
    {reactions(pubtextsearch: "oxygen evolution bajdich 2017") {
      edges {
        node {
          PublicationTitle
          PublicationAuthors
          year
          reactions {
           Reaction
         }
        }
      }
    }}

- Full text search in reactions (chemical composition, facet, reactants, products): 
    {reactions(yextsearch: "OOH Li") {
      edges {
        node {
          Reaction
          publications{
            title
            authors
         }
        }
      }
    }}


- Distinct reactants and products from reactions (works with and without "~"):
    {reactions(reactants: "~OH", products: "~", distinct: true) {
      edges {
        node {
          Reaction
          reactionEnergy
        }
      }
    }}


- ASE structures belonging to reactions:
   {reactions(reactants: "~OH" {
      edges {
        node {
          reactionsSystems {
            systems {
              Cifdata
            }
          }
        }
      } 
    }}


- Distinct ase ids for a particular adsorbate jsonkey (only works if full key
  is given + 'gas'/'star'):
(aseIds: "~", jsonkey: "OOHstar", distinct: true,
            chemicalComposition: "~Co24") {
      edges {
        node {
  	  chemicalComposition
          Reaction
          aseIds
        }
      }
    }}

- Author-name from ase-db: # Doesnt work
    {textKeys(key: "publication_authors", value: "~Bajdich") {
      edges {
        node {
          systems {
            energy
            keyValuePairs
          }
        }
      }
    }}

- Get all distinct DOIs 
   {publications {
      edges {
        node {
          doi
        }
      }
    }}

- Get all entries published since (and including) 2015
    allowed comparisons

   {publications(year: 2015, op: "ge", first:1) {
     edges {
       node {
        id
        year
        systems {
           keyValuePairs
        }
      }
    }
  }}

"""
try:
    import io as StringIO
except:
    # Fallback solution for python2.7
    import StringIO


# global imports
import re
import json
import graphene
import graphene.relay
import graphene_sqlalchemy
import sqlalchemy
import six

# local imports
import models

class CountableConnection(graphene.relay.Connection):
    class Meta:
        abstract = True

    total_count = graphene.Int()

    @staticmethod
    def resolve_total_count(root, info):
        return root.length


class CustomSQLAlchemyObjectType(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, model=None, registry=None,
                                    skip_registry=False, only_fields=(),
                                    exclude_fields=(), connection=None,
                                    use_connection=None, interfaces=(),
                                    id=None, **options):
        # Force it to use the countable connection
        countable_conn = connection or CountableConnection.create_type(
            "{}CountableConnection".format(model.__name__),
            node=cls)

        super(CustomSQLAlchemyObjectType, cls).__init_subclass_with_meta__(
            model,
            registry,
            skip_registry,
            only_fields,
            exclude_fields,
            countable_conn,
            use_connection,
            interfaces,
            id,
            **options)

        
class Publication(CustomSQLAlchemyObjectType):
    
    class Meta:
        model = models.Publication
        interfaces = (graphene.relay.Node,)

    reactions = graphene.List('api.Reaction')
    systems = graphene.List('api.System')


class ReactionSystem(CustomSQLAlchemyObjectType):

    class Meta:
        model = models.ReactionSystem
        interfaces = (graphene.relay.Node, )

    #name = graphene.InputField()
    #systems = graphene.List('api.Systems')
    
class Reaction(CustomSQLAlchemyObjectType):
    
    class Meta:
        model = models.Reaction
        interfaces = (graphene.relay.Node, )
        
    reaction_systems = graphene.List(ReactionSystem)
    
    
class System(CustomSQLAlchemyObjectType):

    _input_file = graphene.String(format=graphene.String())

    class Meta:
        model = models.System
        interfaces = (graphene.relay.Node, )

    @staticmethod
    def resolve__input_file(self, info, format="py"):
        """Return the structure as input for one of several
        DFT codes as supported by ASE. Default format is "py".
        Run

            {systems(last: 1) {
              totalCount
              edges {
                node {
                  InputFile(format:"")
                }
              }
            }}

        to show available formats. Try one of the available formats like,

        {systems(last: 10) {
          totalCount
          edges {
            node {
              InputFile(format:"espresso-in")
            }
          }
        }}

        to generate QE input.

        """
        import ase.io
        import ase.io.formats
        supported_fileformats = [
                key for key, value in ase.io.formats.all_formats.items()
                if value[1].find('F') > 0
                ]
        if format in supported_fileformats:
            mem_file = StringIO.StringIO()
            mem_file.name = 'Export from http://catappdatabase.herokuapp.com/graphql'
            ase.io.write(mem_file, self._toatoms(), format)
            return mem_file.getvalue()
        else:
            return 'Unsupported format. Should be one of %s'\
                % str(supported_fileformats)


class NumberKeyValue(CustomSQLAlchemyObjectType):

    class Meta:
        model = models.NumberKeyValue
        interfaces = (graphene.relay.Node, )


class TextKeyValue(CustomSQLAlchemyObjectType):

    class Meta:
        model = models.TextKeyValue
        interfaces = (graphene.relay.Node, )


class Information(CustomSQLAlchemyObjectType):

    class Meta:
        model = models.Information
        interfaces = (graphene.relay.Node, )


class Key(CustomSQLAlchemyObjectType):

    class Meta:
        model = models.Key
        interfaces = (graphene.relay.Node, )


class Species(CustomSQLAlchemyObjectType):

    class Meta:
        model = models.Species
        interfaces = (graphene.relay.Node, )

#class Search(CustomSQLAlchemyObjectType):
#    class Meta:
#        types = (Publications, Catapp)
#        interfaces = (graphene.relay.Node, )
        
class FilteringConnectionField(graphene_sqlalchemy.SQLAlchemyConnectionField):
    RELAY_ARGS = ['first', 'last', 'before', 'after']
    SPECIAL_ARGS = ['distinct', 'op', 'jsonkey']

    @classmethod
    def get_query(cls, model, info, **args):
        from sqlalchemy import or_
        query = super(FilteringConnectionField, cls).get_query(model, info)
        distinct_filter = False  # default value for distinct
        op = 'eq'
        jsonkey_input = None
        ALLOWED_OPS = ['gt', 'lt', 'le', 'ge', 'eq', 'ne',
                       '=',  '>',  '<',  '>=', '<=', '!=']

        for field, value in args.items():
            if field == 'distinct':
                distinct_filter = value
            elif field == 'op':
                if value in ALLOWED_OPS:
                    op = value
            elif field == 'jsonkey':
                jsonkey_input = value
        
        for field, value in args.items():
            if field not in (cls.RELAY_ARGS + cls.SPECIAL_ARGS):
                from sqlalchemy.sql.expression import func, cast
                jsonb = False
                jsonkey = None
                if '__' in field:
                    field, jsonkey = field.split('__')
                if jsonkey is None:
                    jsonkey = jsonkey_input

                column = getattr(model, field, None)


                if str(column.type) == "TSVECTOR":
                    query = query.filter(column.match("'{}'".format(value)))
                    
                elif str(column.type) == "JSONB":
                    jsonb = True
                    if jsonkey is not None:
                        query = query.filter(column.has_key(jsonkey))
                        column = column[jsonkey].astext
                    values = value.split('+')
                        
                    for value in values:    
                        if value.startswith("~"):
                            column = cast(column, sqlalchemy.String)
                            #if field == 'reactants' or field == 'products':
                            #    column = func.replace(func.replace(column, 'gas', ''), 'star', '')

                            search_string = '%' + value[1:] + '%'
                            
                            if not value == "~":
                                query = query.filter(
                                    column.ilike(search_string))
                            #else:
                            #    query = query.group_by(column)
                            
                        else:
                            if field == 'reactants' or field == 'products':
                                if not 'star' in value and not 'gas' in value:
                                    or_statement = or_(column.has_key(value),
                                                       column.has_key(value +
                                                                      'gas'),
                                                       column.has_key(value +
                                                                      'star'))
                                                   
                                    query = query.filter(or_statement)
                                else:
                                    query = query.filter(column.has_key(value))
                            else:
                                if jsonkey is not None:
                                    query = query.filter(column == value)
                                else:
                                    query = query.filter(column.has_key(value))

                    #if distinct_filter:
                        #TO DO: SELECT DISTINCT jsonb_object_keys(reactants) FROM reaction
                            
                elif isinstance(value, six.string_types):
                    if value.startswith("~"):
                        search_string = '%' + value[1:] + '%'
                        if not query == "~":
                            query = query.filter(column.ilike(search_string))
                    else:
                        query = query.filter(column == value)

                    #if distinct_filter:
                    #     query = query.distinct(column)#.group_by(column)

                else:
                    if op in ['ge', '>=']:
                        query = query.filter(column >= value)
                    elif op in ['gt', '>']:
                        query = query.filter(column > value)
                    elif op in ['lt', '<']:
                        query = query.filter(column < value)
                    elif op in ['le', '<=']:
                        query = query.filter(column <= value)
                    elif op in ['ne', '!=']:
                        query = query.filter(column != value)
                    else:
                        query = query.filter(column == value)
                    

                if distinct_filter:
                    query = query.distinct(column)#.group_by(getattr(model, field))
        return query


def get_filter_fields(model):
    """Generate filter fields (= comparison)
    from graphene_sqlalcheme model
    """
    publication_keys = ['publisher', 'doi', 'title', 'journal', 'authors', 'year']
    filter_fields = {}
    for column_name in dir(model):
        #print('FF {model} => {column_name}'.format(**locals()))
        if not column_name.startswith('_') \
                and not column_name in ['metadata', 'query', 'cifdata']:
            column = getattr(model, column_name)
            column_expression = column.expression

            if '=' in str(column_expression):  # filter out foreign keys
                continue
            elif column_expression is None:  # filter out hybrid properties
                continue
            elif not ('<' in repr(column_expression) and '>' in repr(column_expression)):
                continue

            #column_type = repr(column_expression).split(',')[1].strip(' ()')
            column_type = re.split('\W+', repr(column_expression))

            column_type = column_type[2]
            if column_type == 'Integer':
                filter_fields[column_name] = getattr(graphene, 'Int')()
            elif column_type == 'TSVECTOR':
                filter_fields[column_name] = getattr(graphene, 'String')()
            elif column_type == 'JSONB':
                filter_fields[column_name] = getattr(graphene, 'String')()
            else:
                filter_fields[column_name] = getattr(graphene, column_type)()
    # always add a distinct filter
    filter_fields['distinct'] = graphene.Boolean()
    filter_fields['op'] = graphene.String()
    filter_fields['search'] = graphene.String()
    filter_fields['jsonkey'] = graphene.String()
    
    return filter_fields

class Query(graphene.ObjectType):
    node = graphene.relay.Node.Field()
    information = FilteringConnectionField(
        Information, **get_filter_fields(models.Information))
    systems = FilteringConnectionField(
        System, **get_filter_fields(models.System))
    species = FilteringConnectionField(
        Species, **get_filter_fields(models.Species))
    key = FilteringConnectionField(Key, **get_filter_fields(models.Key))
    text_keys = FilteringConnectionField(
        TextKeyValue, **get_filter_fields(models.TextKeyValue))
    number_keys = FilteringConnectionField(
        NumberKeyValue, **get_filter_fields(models.NumberKeyValue))
    reactions = FilteringConnectionField(
        Reaction, **get_filter_fields(models.Reaction))
    reaction_systems = FilteringConnectionField(
        ReactionSystem, **get_filter_fields(models.ReactionSystem))
    publications = FilteringConnectionField(
        Publication, **get_filter_fields(models.Publication))


schema = graphene.Schema(
    query=Query, types=[System, Species, TextKeyValue, NumberKeyValue, Key, Reaction, ReactionSystem, Publication
    ])
