# -*- coding: utf-8 -*-

import json
import math
import sys
import os
sys.path.append('C:\Users\Sunghyun\Anaconda2\Lib\site-packages')

from binaryninja import (BinaryViewType, MediumLevelILInstruction,
                         MediumLevelILOperation, RegisterValueType,
                         SSAVariable)
from tqdm import tqdm
from z3 import (UGT, ULT, And, Array, BitVec, BitVecSort, Concat, Extract,
                LShR, Not, Or, Solver, ZeroExt, simplify, unsat)
#BlackHighlightColor= 9
#BlueHighlightColor= 1
#CyanHighlightColor= 3
#GreenHighlightColor= 2
#MagentaHighlightColor= 5
#NoHighlightColor= 0
#OrangeHighlightColor= 7
#RedHighlightColor= 4
#WhiteHighlightColor= 8
#YellowHighlightColor= 6

def SetColor(address):
	address.highlight = COLOR


def Backward_Highlight(incomging_edge_list):
	for incoming_edge in incomging_edge_list:
		if incoming_edge.source in covered_block_list:
			print "Skip to blocks already covered."
		else:
			covered_block_list.append(incoming_edge.source)
			SetColor(incoming_edge.source)
			
			print "Now Block Address", incoming_edge.source
			print "incoming_edge.source.incoming_edges", incoming_edge.source.incoming_edges
			next_incomging_edge_list = incoming_edge.source.incoming_edges
			
			print "next_incomging_edge_list",next_incomging_edge_list
			print "\n"
			new_list = []
			for next_incomging_edge in next_incomging_edge_list:
				print "  -> incoming_edge.source.start", hex(incoming_edge.source.start)
				print "  -> next_incomging_edge.source.start", hex(next_incomging_edge.source.start)
				if incoming_edge.source.start > next_incomging_edge.source.start:
					new_list.append(next_incomging_edge)
				elif next_incomging_edge._type is BranchType.IndirectBranch:
					new_list.append(next_incomging_edge)
			next_incomging_edge_list = new_list
			Backward_Highlight(next_incomging_edge_list)

	
	

print "Backward CFG start.."

COLOR = HighlightStandardColor.YellowHighlightColor
now_address = 0x1c00de20
bb = bv.get_basic_blocks_at(now_address)
SetColor(bb[0])

incomging_edge_list = bb[0].incoming_edges

global covered_block_list
covered_block_list = []

Backward_Highlight(incomging_edge_list)

print "Backward CFG Complete.."