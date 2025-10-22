from typing import Dict, Any, List, Optional
from facility import Facility

# Define a class for the supply chain
class SupplyChain:
	def __init__(self):
		self.facilities = {}   # facility_id : Facility
		self.links = {}        # (from_fac,to_fac): {products: fraction_transferred}

	def add_facility(self, fac_id, fac):
		self.facilities[fac_id] = fac

	def link_facilities(self, from_fac, to_fac, products):
		'''
		from_fac (str): name of the source facility
		to_fac (str): name of the target facility
		products (dict): {product names: % of product to transfer to new facility}
		'''
		if from_fac not in self.facilities:
			raise KeyError(f"Source facility '{source_name}' not found.")
		if to_fac not in self.facilities:
			raise KeyError(f"Target facility '{target_name}' not found.")

		key = (from_fac, to_fac)
		if key not in self.links:
			self.links[key] = {}

		# Validate products exist
		from_outputs = self.facilities[from_fac].collect_primary_outputs()
		to_inputs = self.facilities[to_fac].collect_primary_inputs()

		for product in products.keys():
			if product not in from_outputs:
				raise KeyError(f"Product '{product}' not found in {from_fac} outputs.")
			if product not in to_inputs:
				raise KeyError(f"Product '{product}' not found in {to_fac} inputs.")

		self.links[key].update(products)

	def propagate_materials(self):
		"""Push coproduct outputs from one facility into another’s inputs."""
		for (from_id, to_id), products in self.links.items(): # Really this should be an ordered list, but not necessary for now
			from_fac = self.facilities[from_id]
			to_fac = self.facilities[to_id]

			outputs = from_fac.collect_primary_outputs()

			for product, frac in products.items():
				if product not in outputs:
					continue  # skip missing product - shouldn't be possible, but keep code here just in case

				composition = outputs[product]["constituents"]

				# Pass to target facility
				to_fac.add_input_comp(
					primary_input=product,
					input_composition=composition,
					propagate=True
				)

			# Re-calculate volume in to_fac based on new input composition
			to_fac.calculate_all(to_fac.apv)

			# Based on the volume defining output in the from_fac, calculate the volume in from_fac


			produced_volume = outputs[product]["volume"]
			transfer_amount = produced_volume * frac
