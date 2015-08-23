"""
Some very thin wrapper classes around those in OWSLib
for convenience.
"""

import logging

from owslib.etree import etree
from owslib.fes import PropertyIsEqualTo
from owslib.fes import PropertyIsLike
from owslib.fes import PropertyIsBetween
from owslib.fes import PropertyIsEqualTo
from owslib.fes import BBox
from owslib.fes import PropertyIsNotEqualTo


log = logging.getLogger(__name__)

class CswError(Exception):
    pass

class OwsService(object):
    def __init__(self, endpoint=None):
        if endpoint is not None:
            self._ows(endpoint)

    def __call__(self, args):
        return getattr(self, args.operation)(**self._xmd(args))

    @classmethod
    def _operations(cls):
        return [x for x in dir(cls) if not x.startswith("_")]

    def _xmd(self, obj):
        md = {}
        for attr in [x for x in dir(obj) if not x.startswith("_")]:
            val = getattr(obj, attr)
            if not val:
                pass
            elif callable(val):
                pass
            elif isinstance(val, basestring):
                md[attr] = val
            elif isinstance(val, int):
                md[attr] = val
            elif isinstance(val, list):
                md[attr] = val
            else:
                md[attr] = self._xmd(val)
        return md

    def _ows(self, endpoint=None, **kw):
        if not hasattr(self, "_Implementation"):
            raise NotImplementedError("Needs an Implementation")
        if not hasattr(self, "__ows_obj__"):
            if endpoint is None:
                raise ValueError("Must specify a service endpoint")
            self.__ows_obj__ = self._Implementation(endpoint)
        return self.__ows_obj__

    def getcapabilities(self, debug=False, **kw):
        ows = self._ows(**kw)
        caps = self._xmd(ows)
        if not debug:
            if "request" in caps: del caps["request"]
            if "response" in caps: del caps["response"]
        if "owscommon" in caps: del caps["owscommon"]
        return caps

class CswService(OwsService):
    """
    Perform various operations on a CSW service
    """
    from owslib.csw import CatalogueServiceWeb as _Implementation
    def getrecords(self, qtype=None, keywords=[],
                   typenames="csw:Record", esn="brief",
                   skip=0, count=10, outputschema="gmd", **kw):
        from owslib.csw import namespaces
        constraints = []
        csw = self._ows(**kw)

        if qtype is not None:
           constraints.append(PropertyIsEqualTo("dc:type", qtype))

        kwa = {
            "constraints": constraints,
            "typenames": typenames,
            "esn": esn,
            "startposition": skip,
            "maxrecords": count,
            "outputschema": namespaces[outputschema],
            }
        log.info('Making CSW request: getrecords2 %r', kwa)
        csw.getrecords2(**kwa)
        if csw.exceptionreport:
            err = 'Error getting records: %r' % \
                  csw.exceptionreport.exceptions
            #log.error(err)
            raise CswError(err)
        return [self._xmd(r) for r in csw.records.values()]

    def getidentifiers(self, qtype=None, typenames="csw:Record", esn="brief",
                       keywords=[], limit=None, page=10, outputschema="gmd",
                       startposition=0, cql=None, constraints=[], **kw):
        from owslib.csw import namespaces
        csw = self._ows(**kw)

        constraints = self._parse_constraints(constraints)
        if qtype is not None:
           constraints.append(PropertyIsEqualTo("dc:type", qtype))

        kwa = {
            "constraints": constraints,
            "typenames": typenames,
            "esn": esn,
            "startposition": startposition,
            "maxrecords": page,
            "outputschema": namespaces[outputschema],
            "cql":cql,
            }
        i = 0
        matches = 0
        while True:
            log.info('Making CSW request: getrecords2 %r', kwa)

            csw.getrecords2(**kwa)
            if csw.exceptionreport:
                err = 'Error getting identifiers: %r' % \
                      csw.exceptionreport.exceptions
                #log.error(err)
                raise CswError(err)

            if matches == 0:
                matches = csw.results['matches']

            identifiers = csw.records.keys()
            if limit is not None:
                identifiers = identifiers[:(limit-startposition)]
            for ident in identifiers:
                yield ident

            if len(identifiers) == 0:
                break

            i += len(identifiers)
            if limit is not None and i > limit:
                break

            startposition += page
            if startposition >= (matches + 1):
                break

            kwa["startposition"] = startposition

    def getrecordbyid(self, ids=[], esn="full", outputschema="gmd", **kw):
        from owslib.csw import namespaces
        csw = self._ows(**kw)
        kwa = {
            "esn": esn,
            "outputschema": namespaces[outputschema],
            }
        # Ordinary Python version's don't support the metadata argument
        log.info('Making CSW request: getrecordbyid %r %r', ids, kwa)
        csw.getrecordbyid(ids, **kwa)
        if csw.exceptionreport:
            err = 'Error getting record by id: %r' % \
                  csw.exceptionreport.exceptions
            #log.error(err)
            raise CswError(err)
        if not csw.records:
            return
        record = self._xmd(csw.records.values()[0])

        ## strip off the enclosing results container, we only want the metadata
        #md = csw._exml.find("/gmd:MD_Metadata")#, namespaces=namespaces)
        # Ordinary Python version's don't support the metadata argument
        md = csw._exml.find("/{http://www.isotc211.org/2005/gmd}MD_Metadata")
        mdtree = etree.ElementTree(md)
        try:
            record["xml"] = etree.tostring(mdtree, pretty_print=True, encoding=unicode)
        except TypeError:
            # API incompatibilities between different flavours of elementtree
            try:
                record["xml"] = etree.tostring(mdtree, pretty_print=True, encoding=unicode)
            except AssertionError:
                record["xml"] = etree.tostring(md, pretty_print=True, encoding=unicode)

        record["xml"] = '<?xml version="1.0" encoding="UTF-8"?>\n' + record["xml"]
        record["tree"] = mdtree
        return record

    def _parse_constraints(self, constraints_config):
        constraints_parsed = []
        for constraint_group_config in constraints_config:
            if(isinstance(constraint_group_config, list)):
                constraint_group = self._parse_constraint_group(constraint_group_config)
                if(constraint_group):
                    constraints_parsed.append(constraint_group)
            else:
                constraint = self._parse_constraint(constraint_group_config)
                if(constraint):
                    constraints_parsed.append(constraint)
        return constraints_parsed

    def _parse_constraint_group(self, constraint_group_config):
        """
            The group is correspond to AND clause, i.e.,
            all of the element in the group should be satisfied
            at the same time
        """
        constraints_parsed = []
        for constraint_config in constraint_group_config:
            constraint = self._parse_constraint(constraint_config)
            if(constraint):
                constraints_parsed.append(constraint)
        return constraints_parsed

    def _parse_constraint(self, constraint_config):
        if(constraint_config['type'] == 'PropertyIsLike'):
            if(not ('propertyname' in constraint_config and 'literal' in constraint_config)):
                #silent fail --> config is not correct
                return False
            else:
                return PropertyIsLike(
                    propertyname=constraint_config['propertyname'],
                    literal=constraint_config['literal']
                )
        elif(constraint_config['type'] == 'PropertyIsBetween'):
            if(not ('propertyname' in constraint_config and 'lower' in constraint_config and 'upper' in constraint_config)):
                #silent fail --> config is not correct
                return False
            else:
                return PropertyIsBetween(
                    propertyname=constraint_config['propertyname'],
                    lower=constraint_config['lower'],
                    upper=constraint_config['upper']
                )
        elif(constraint_config['type'] == 'PropertyIsEqualTo'):
            if(not ('propertyname' in constraint_config and 'literal' in constraint_config)):
                #silent fail --> config is not correct
                return False
            else:
                return PropertyIsEqualTo(
                    propertyname=constraint_config['propertyname'],
                    literal=constraint_config['literal']
                )
        elif(constraint_config['type'] == 'PropertyIsNotEqualTo'):
            if(not ('propertyname' in constraint_config and 'literal' in constraint_config)):
                #silent fail --> config is not correct
                return False
            else:
                return PropertyIsNotEqualTo(
                    propertyname=constraint_config['propertyname'],
                    literal=constraint_config['literal']
                )
        elif(constraint_config['type'] == 'BoundingBox'):
            if(not ('LowerCorner' in constraint_config and 'UpperCorner' in constraint_config)):
                return False
            else:
                bbox = constraint_config['LowerCorner'].split() + constraint_config['UpperCorner'].split()
                return BBox(bbox)
        else:
            return False
