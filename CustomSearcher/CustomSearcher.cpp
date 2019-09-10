///
/// Copyright (C) 2011-2015, Dependable Systems Laboratory, EPFL
/// Copyright (C) 2016, Cyberhaven
/// All rights reserved.
///
/// Licensed under the Cyberhaven Research License Agreement.
///

/**
 * This plugin implements a cooperative searcher.
 * The current state is run until the running program expicitely
 * asks to schedule another one, akin to cooperative scheduling.
 *
 * This searcher is useful for debugging S2E, becauses it allows
 * to control the sequence of executed states.
 *
 * RESERVES THE CUSTOM OPCODE 0xAB
 */

#include <s2e/cpu.h>
#include <s2e/opcodes.h>

#include <s2e/ConfigFile.h>
#include <s2e/S2E.h>
#include <s2e/S2EExecutor.h>
#include <s2e/Utils.h>

#include <iostream>

#include "CustomSearcher.h"

namespace s2e {
namespace plugins {

using namespace llvm;

S2E_DEFINE_PLUGIN(CustomSearcher, "Custom searcher", "CustomSearcher");

void CustomSearcher::initialize() {
    s2e()->getExecutor()->setSearcher(this);
    m_address = (uint64_t) s2e()->getConfig()->getInt(getConfigKey() + ".addressToTrack");
    debug = true;// s2e()->getConfig()->getBool(getConfigKey() + ".debug");
}

klee::ExecutionState &CustomSearcher::selectState() {
    S2EExecutionState* ris = NULL;
    if(!state_group1.empty()){
        ris = state_group1.back();
    }
    else{
        ris = state_group2.back();
    }

    if (debug) {
        uint64_t ip = 0x0;
        if (ris->regs())
            ip = ris->regs()->getPc();
        getInfoStream(ris) <<
            "Selecting state ID: " << ris->getID() <<
            " GID: " << ris->getGuid() <<
            " IP: " << ip << "\n";
        for(int i=0 ; i<state_group1.size(); i++){
            S2EExecutionState* tmp_ris =state_group1.at(i); 
            getInfoStream(tmp_ris) <<
            "[Ready - state_group1] state ID : " <<tmp_ris->getID()  <<
            " at pc = " << hexval(tmp_ris->regs()->getPc()) <<  "\n";
        }
        for(int i=0 ; i<state_group2.size(); i++){
            S2EExecutionState* tmp_ris =state_group2.at(i); 
            getInfoStream(tmp_ris) <<
            "[Ready - state_group2] state ID : " <<tmp_ris->getID()  <<
            " at pc = " << hexval(tmp_ris->regs()->getPc()) <<  "\n";
        }
    }
    return *ris;
}

void CustomSearcher::update(klee::ExecutionState *current, const klee::StateSet &addedStates,
                                 const klee::StateSet &removedStates) {

    S2EExecutionState *s2eCurrent = static_cast<S2EExecutionState *>(current);

    if (debug && (addedStates.size() > 0 || removedStates.size() > 0)) {
        getInfoStream(s2eCurrent) <<
          "Current state ID: " << s2eCurrent->getID() <<
          " GID: " << s2eCurrent->getGuid() <<
          " len(added): " << addedStates.size() <<
          " len(removed): " << removedStates.size() << "\n";
    }

    foreach2 (it, addedStates.begin(), addedStates.end()) {
        S2EExecutionState *state = static_cast<S2EExecutionState *>(*it);
        
        uint64_t staticTargets[1];
        state->getStaticTarget(&staticTargets[0]);

        if(staticTargets[0] == m_address){
            state_group1.push_back(state);
        }
        else{
            state_group2.push_back(state);
        }

        if (debug) {
            getInfoStream(s2eCurrent) <<
                "Adding state ID: " << state->getID() <<
                " dest branch:" << hexval(staticTargets[0]) << 
                " target branch:" << hexval(m_address) << "\n";
        }
    }

    foreach2 (it, removedStates.begin(), removedStates.end()) {
        S2EExecutionState *state = static_cast<S2EExecutionState *>(*it);
        bool ok = false;
        

        for (std::vector<S2EExecutionState *>::iterator it = state_group1.begin(), ie = state_group1.end(); it != ie; ++it) {
            if (state == *it) {
                state_group1.erase(it);
                ok = true;
                break;
            }
        }
        
        for (std::vector<S2EExecutionState *>::iterator it = state_group2.begin(), ie = state_group2.end(); it != ie; ++it) {
            if (state == *it) {
                state_group2.erase(it);
                ok = true;
                break;
            }
        }
        assert(ok && "invalid state removed");

        if (debug) {
            getInfoStream(s2eCurrent) <<
                "Removing state ID: " << state->getID() <<
                " GID: " << state->getGuid() << "\n";
        }
    }

}

bool CustomSearcher::empty() {
    return state_group2.empty();
}

} // namespace plugins
} // namespace s2e
