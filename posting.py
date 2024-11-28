from dataclasses import dataclass, field
from typing import List, Type

@dataclass
class Instance:
	position: int
	styleScore: int
	
	def __str__(self) -> str:
		return f"{self.position},{self.styleScore}"

class Posting:
	def __init__(self, docID: int, tfScore: float, instance: List[Instance]) -> None:
		self.docID: int = docID
		self.tfScore: float = tfScore
		self.instances: List[Type[Instance]] = instance
	
	def addInstance(self, instance: Instance) -> None:
		self.instances.append(instance)

	def __str__(self) -> str:
		string = ""
		for x in range(len(self.instances)):
			string += f"{self.instances[x]}"
			if x != len(self.instances)-1:
				string += "|"
		return f"{self.docID},{self.tfScore}={string}"

if __name__ == "__main__":
	i0 = Instance(1, 5)
	i1 = Instance(2, 2)
	p = Posting(1, 0.6, [i0, i1])
	print(p)
