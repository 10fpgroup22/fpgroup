from minilib import Loader
from typing import Union, Any


class Settings(Loader):
	__fields__ = {"groups": "_groups"}

	def __init__(self):
		self._groups = {}

	def add(self, group: str):
		self[group] = {}
		return self[group]

	def set(self, group: str, name: str, value: Any):
		self[group, name] = value
		return value

	def remove(self, group: str, name: Optional[str] = None):
		del self[group, name], group, name

	def get(self, group: str, name: Optional[str] = None):
		return self[group, name]

	def iter_group(self, group: str):
		return self._groups.get(group, {}).items()

	def __getitem__(self, item: Union[str, tuple]):
		group, name = item if isinstance(item, tuple) else [item, None]

		if not (type(group) == str and type(name) in [str, type(None)]):
			raise TypeError(f"Failed to get '{name}' of '{group}'. Check for type 'item' attribute")

		if name:
			return self._groups.get(group, {}).get(name, None)

		return self._groups.get(group, {})

	def __delitem__(self, item: Union[str, tuple]):
		group, name = item if isinstance(item, tuple) else [item, None]

		if not (type(group) == str and type(name) in [str, type(None)]):
			raise TypeError(f"Failed to delete '{name}' of '{group}'. Check for type 'item' attribute")

		if name:
			del self._groups[group][name]
		else:
			del self._groups[group]

	def __setitem__(self, item: Union[str, tuple], value: Any):
		group, name = item if isinstance(item, tuple) else [item, None]

		if not (type(group) == str and type(name) == str):
			raise TypeError(f"Failed to set '{name}' of '{group}'. Check for type 'item' attribute")

		grp = self._groups.setdefault(group, {})
		grp[name] = value
