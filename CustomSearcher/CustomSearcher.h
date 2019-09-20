//
// Created by luca on 05/12/18.
//

#ifndef LIBS2EPLUGINS_CUSTOMSEARCHER_H
#define LIBS2EPLUGINS_CUSTOMSEARCHER_H
#include <s2e/CorePlugin.h>
#include <s2e/Plugin.h>

#include <s2e/S2EExecutionState.h>
#include <s2e/Plugins/OSMonitors/ModuleDescriptor.h>
#include <s2e/Plugins/OSMonitors/Support/ModuleExecutionDetector.h>
#include <klee/Searcher.h>

#include <vector>

namespace s2e {
namespace plugins {
class ModuleMap;
class OSMonitor;
class CustomSearcher : public Plugin, public klee::Searcher {
    S2E_PLUGIN
public:

    CustomSearcher(S2E *s2e) : Plugin(s2e) {
    }
    void initialize();

    virtual klee::ExecutionState &selectState();

    virtual void update(klee::ExecutionState *current, const klee::StateSet &addedStates,
                        const klee::StateSet &removedStates);

    void onFork(S2EExecutionState *state, const std::vector<S2EExecutionState *> &newStates,
                const std::vector<klee::ref<klee::Expr>> &newConditions);

    virtual bool empty();

private:
    //typedef llvm::DenseMap<uint64_t, uint64_t> ForkCounts;
    //typedef std::map<std::string, ForkCounts> ModuleForkCounts;

    //ModuleForkCounts m_forkCount;
    uint64_t initial_count;
    ModuleExecutionDetector *m_detector;
    std::vector<S2EExecutionState*> state_group1;
    std::vector<S2EExecutionState*> state_group2;
    std::vector<uint64_t> m_addresses;
    bool debug;
};

} // namespace plugins
} // namespace s2e

#endif //LIBS2EPLUGINS_CUSTOMSEARCHER_H
