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
#include <s2e/Plugins/OSMonitors/OSMonitor.h>
#include <s2e/Plugins/OSMonitors/Support/ModuleMap.h>
#include <s2e/Plugins/OSMonitors/ModuleDescriptor.h>

#include <iostream>

#include "CustomSearcher.h"

namespace s2e {
namespace plugins {

using namespace llvm;

S2E_DEFINE_PLUGIN(CustomSearcher, "Custom searcher", "CustomSearcher","OSMonitor","ModuleMap", "ModuleExecutionDetector");

void CustomSearcher::initialize() {
    m_detector = s2e()->getPlugin<ModuleExecutionDetector>();
    s2e()->getCorePlugin()->onStateFork.connect(sigc::mem_fun(*this, &CustomSearcher::onFork));
    s2e()->getExecutor()->setSearcher(this);
    m_addresses = s2e()->getConfig()->getIntegerList(getConfigKey() + ".addressToTrack");
    debug = true; // s2e()->getConfig()->getBool(getConfigKey() + ".debug");
    initial_count = 0;

}

void CustomSearcher::onFork(S2EExecutionState *state, const std::vector<S2EExecutionState *> &newStates, const std::vector<klee::ref<klee::Expr>> &newConditions) {

    /* Config file Test */
    // getInfoStream(state) << "Config File Test .. " << m_addresses.size() << "\n";
    // std::vector<uint64_t>::iterator iter=m_addresses.begin();
    // for (iter = m_addresses.begin(); iter != m_addresses.end(); ++iter){
    //     getInfoStream(state) << hexval(*iter) << "\n";
    // }
    
    /* Update the fork count stats */
    auto module = m_detector->getCurrentDescriptor(state);
    getInfoStream(state) << "[sunghyun] Forking!" << "\n";
    uint64_t curPc = 0;
    int signal = 0;

    foreach2 (it2, newStates.begin(), newStates.end()) {
        if (module) {
            getInfoStream(*it2) << "[sunghyun] Forked Module name : " << module->Name << "\n";
            
            uint64_t staticTargets[1];
            uint64_t originalTargets[1];
            state->getStaticTarget(&originalTargets[0]);
            (*it2)->getStaticTarget(&staticTargets[0]);
            curPc = module->ToNativeBase(staticTargets[0]);
            getInfoStream(*it2) << "[sunghyun] Forked ToNativeBase : " << hexval(curPc) << "\n";

            
            if(state->getID() != (*it2)->getID() && curPc < 0x7f0000000000){
                std::vector<uint64_t>::iterator iter=m_addresses.begin();
                for (iter = m_addresses.begin(); iter != m_addresses.end(); ++iter){
                    if(curPc == *iter){
                        state_group1.push_back(*it2);
                        signal = 1;
                    }
                }
                if(signal == 0){
                    state_group2.push_back(*it2);
                    signal = 0;
                }
            }
            else{
                s2e()->getExecutor()->terminateState(*it2, "[Terminate State] Strange Address..");
            }
        }
    }
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
        if(initial_count == 0){
            state_group2.push_back(state);
            initial_count++;
        }
        if (debug) {
            getInfoStream(s2eCurrent) <<
                "Adding state ID: " << state->getID() << "\n";
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
