import sys
from importlib import import_module
from threading import Lock
from types import ModuleType

from auto_salience import auto_set_salience
from func import RuleFunc
from slots import HasSlots
from ruledef import RuleDef, params
from utils import logger

class DefModuleLoader(object):
    def __init__(self, engine):
        self.engine = engine
        self.lock = Lock()
        self.logger = logger.getChild(type(self).__name__)
        
    def load(self, module_name, package=None, auto_salience=True, **module_params):
        # Prepare for import
        if isinstance(package, ModuleType):
            package = package.__name__
        if package is not None and '.' not in module_name:
            module_name = '.' + module_name
        self.logger.debug('Loading: %s', module_name)
            
        # Import module, while keeping track of entities that require compilation
        existing_modules = set(sys.modules)
        with self.lock:
            params.update(module_params)
            RuleDef._all_instances = []
            HasSlots._all_subclasses = []
            RuleFunc._set_cur_engine(self.engine)
            module = import_module(module_name, package)
            if module.__name__ in existing_modules:
                reload(module)
            # TODO: Why are there non-named templates??
            templates_to_build = [x for x in HasSlots._all_subclasses if x._name is not None]
            rules_to_build = RuleDef._all_instances

        # Add name to all unnamed instances (according to variable name)
        for name in dir(module):
            entity = getattr(module, name)
            if isinstance(entity, RuleDef):
                entity._set_name(name) # TODO: include module name
                
        if auto_salience:
            auto_set_salience(RuleDef._all_instances)

        # Sort for clarity
        templates_to_build.sort(key=lambda x:x._name)
        rules_to_build.sort(key=lambda x:(-(x._rule.salience or 0), x._rule.name))
                
        # Compile everything, except unnamed templates (which cannot be compiled)
        # Note that RuleDefs also may contain TemplateDefs, which would not be named.
        for entity in templates_to_build + rules_to_build:
            entity._build(self.engine)
