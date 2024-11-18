from . system import printd

class Settings:

    _properties = {}
    _prop_names = {}

    def init_settings(self, props=[]):
        if (idname := self.bl_idname) not in self._properties:
            self._properties[idname] = {}
            self._prop_names[idname] = {}

        self._prop_names[idname] = []

        for name in props:
            self._prop_names[idname].append(name)

    def save_settings(self):
        prop_names = self._prop_names[self.bl_idname]

        for name in dir(self.properties):
            if name in prop_names:
                try:
                    self._properties[self.bl_idname][name] = getattr(self.properties, name)
                except:
                    pass

    def load_settings(self):
        props = self._properties[self.bl_idname]
        
        for name in props:
            self.properties[name] = props[name]
