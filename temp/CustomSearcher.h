//
// Created by luca on 05/12/18.
//

#ifndef LIBS2EPLUGINS_CUSTOMSEARCHER_H
#define LIBS2EPLUGINS_CUSTOMSEARCHER_H
#include <s2e/CorePlugin.h>
#include <s2e/Plugin.h>

#include <s2e/S2EExecutionState.h>
#include <s2e/Plugins/OSMonitors/ModuleDescriptor.h>
#include <klee/Searcher.h>

#include <vector>

namespace s2e {
namespace plugins {
class ModuleMap;
class CustomSearcher : public Plugin, public klee::Searcher {
    S2E_PLUGIN
public:

    CustomSearcher(S2E *s2e) : Plugin(s2e) {
    }
    void initialize();

    virtual klee::ExecutionState &selectState();

    virtual void update(klee::ExecutionState *current, const klee::StateSet &addedStates,
                        const klee::StateSet &removedStates);

    virtual bool empty();

private:
    ModuleMap *m_modules;
    std::vector<S2EExecutionState*> state_group1;
    std::vector<S2EExecutionState*> state_group2;
    bool debug;
    uint64_t m_address;
};

} // namespace plugins
} // namespace s2e

#endif //LIBS2EPLUGINS_CUSTOMSEARCHER_H
