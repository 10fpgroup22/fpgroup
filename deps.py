from minilib import Loader
from typing import Any, Optional, Union

__all__ = ["Settings"]


class Settings(Loader):
	__fields__ = {"groups": "_groups"}
	_groups: dict[str, dict[str, Any]] = {}

	def add(self, group: str):
		self[group] = {}
		return self[group]

	def get(self, group: str, name: Optional[str] = None):
		return self[group, name]

	def set(self, group: str, name: str, value: Any):
		self[group, name] = value
		return self[group]

	def delete(self, group: str, name: Optional[str] = None):
		del self[group, name]
		return self[group]

	def iter_group(self, group: str):
		return iter(self[group].items())

	def __iter__(self):
		return iter(self._groups.items())

	def __contains__(self, val: str):
		return val in self._groups

	def __getitem__(self, items: Union[str, tuple]):
		group, name = items if isinstance(items, tuple) else [items, None]
		
		if name:
			return self._groups.get(group, {}).get(name, None)

		return self._groups.get(group, {})

	def __setitem__(self, items: Union[str, tuple], value: Any):
		group, name = items if isinstance(items, tuple) else [items, None]
		if name:
			self._groups[group][name] = value
		else:
			self._groups[group] = value if isinstance(value, dict) else self._groups.get(group, {})

	def __delitem__(self, items: Union[str, tuple]):
		group, name = items if isinstance(items, tuple) else [items, None]
		if name:
			del self._groups[group][name]
		else:
			del self._groups[group]
